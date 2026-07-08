import json
import os
import time

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from config.settings import AZURE_ORGANIZATION, AZURE_PROJECT, AZURE_PAT


class AzureService:
    def __init__(self, historico_path=os.path.join("data", "historias_processadas.json"), timeout=20):
        self.auth = HTTPBasicAuth('', AZURE_PAT or '')
        self.headers = {'Content-Type': 'application/json'}
        self.historico_path = historico_path
        self.timeout = timeout

        if not os.path.exists(os.path.dirname(self.historico_path)):
            os.makedirs(os.path.dirname(self.historico_path), exist_ok=True)

    def _request_with_retry(self, method, url, *, max_retries=3, **kwargs):
        kwargs.setdefault("headers", self.headers)
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, timeout=self.timeout, auth=self.auth, **kwargs)
                response.raise_for_status()
                return response
            except RequestException as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️ [Azure] Falha na requisição ({method.upper()} {url}) tentativa {attempt + 1}/{max_retries}: {exc}. Tentando novamente em {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ [Azure] Falha persistente na requisição ({method.upper()} {url}): {exc}")
                    raise

        raise last_error

    def carregar_historico(self):
        if os.path.exists(self.historico_path):
            try:
                with open(self.historico_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def salvar_historico(self, historico):
        with open(self.historico_path, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=4)

    def buscar_todos_filhos_do_epico(self, epic_id):
        """
        Dado o ID de um Épico, faz uma query Wiql para trazer
        todas as User Stories filhas dele, independentemente da coluna do board.
        """
        wiql_url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/wiql?api-version=7.1"
        query_filhos = {
            "query": f"""
                SELECT [System.Id]
                FROM WorkItemLinks
                WHERE [Source].[System.Id] = {epic_id}
                  AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
                  AND [Target].[System.WorkItemType] = 'User Story'
            """
        }
        response = self._request_with_retry("post", wiql_url, json=query_filhos)
        if response.status_code == 200:
            relations = response.json().get('workItemRelations', [])
            return [rel['target']['id'] for rel in relations if rel.get('target')]
        return []

    def buscar_detalhes_em_lote(self, ids_list):
        """Abre os detalhes de um grupo de IDs de uma vez só."""
        if not ids_list:
            return []
        ids_string = ",".join(map(str, ids_list))
        details_url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/workitems?ids={ids_string}&$expand=relations&api-version=7.1"
        response = self._request_with_retry("get", details_url)
        if response.status_code == 200:
            return response.json().get('value', [])
        return []

    def buscar_historias_novas_sortimento(self):
        colunas_monitoradas = [
            "Aguardando Dev",
            "Dev",
            "Aguardando QA",
            "QA",
            "Aguard. HML de Negócio"
        ]
        condicoes_colunas = " OR ".join(
            [f"[System.BoardColumn] = '{coluna}'" for coluna in colunas_monitoradas]
        )

        wiql_url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/wiql?api-version=7.1"
        query_wiql = {
            "query": f"""
                SELECT [System.Id]
                FROM WorkItems
                WHERE [System.TeamProject] = '{AZURE_PROJECT}'
                  AND [System.WorkItemType] = 'User Story'
                  AND ({condicoes_colunas})
            """
        }

        print(f"🔍 [Azure] Conectando à API e monitorando as colunas: {', '.join(colunas_monitoradas)}...")

        try:
            response = self._request_with_retry("post", wiql_url, json=query_wiql)
        except RequestException as exc:
            print(f"❌ [Azure] Não foi possível consultar as histórias nas colunas monitoradas: {exc}")
            return None, []

        if response.status_code != 200:
            print(f"❌ Erro na query do Azure: {response.status_code} - {response.text}")
            return None, []

        items = response.json().get('workItems', [])
        ids_na_coluna_gatilho = [item['id'] for item in items]

        if not ids_na_coluna_gatilho:
            print("⚠️ [Azure] Nenhuma história encontrada nas colunas monitoradas no momento.")
            return {}, []

        try:
            detalhes_gatilho = self.buscar_detalhes_em_lote(ids_na_coluna_gatilho)
        except RequestException as exc:
            print(f"❌ [Azure] Falha ao buscar detalhes das histórias da coluna: {exc}")
            return None, []

        historico_antigo = self.carregar_historico()

        epicos_para_processar = set()
        ids_ancoras_novos = []

        for story in detalhes_gatilho:
            fields = story['fields']
            area_path = fields.get('System.AreaPath', '')

            if "Dynamic_Assortment_Services" not in area_path:
                continue

            story_id = story['id']

            if story_id not in historico_antigo:
                ids_ancoras_novos.append(story_id)

                relations = story.get('relations', [])
                for rel in relations:
                    if rel['rel'] == 'System.LinkTypes.Hierarchy-Reverse':
                        epic_id = rel['url'].split('/')[-1]
                        epicos_para_processar.add(epic_id)
                        break

        if not epicos_para_processar:
            return {}, []

        print(f"🎯 [Mapeamento] {len(ids_ancoras_novos)} história(s) nova(s) dispararam o alerta para {len(epicos_para_processar)} Épico(s).")

        epicos_agrupados = {}
        todos_ids_historias_envolvidas = []

        for epic_id in epicos_para_processar:
            print(f"🧬 [Captura] Mapeando árvore completa do Épico #{epic_id} no Azure DevOps...")

            try:
                ids_filhos_totais = self.buscar_todos_filhos_do_epico(epic_id)
            except RequestException as exc:
                print(f"⚠️ [Azure] Não foi possível processar o épico #{epic_id} devido a erro de rede: {exc}")
                continue

            if not ids_filhos_totais:
                continue

            try:
                detalhes_filhos = self.buscar_detalhes_em_lote(ids_filhos_totais)
            except RequestException as exc:
                print(f"⚠️ [Azure] Não foi possível buscar os detalhes do épico #{epic_id}: {exc}")
                continue

            epicos_agrupados[epic_id] = {
                "criterio_epic": "Sem critérios no Épico.",
                "historias": []
            }

            for child in detalhes_filhos:
                child_fields = child['fields']
                child_id = child['id']
                child_title = child_fields.get('System.Title', '')
                child_crit = child_fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', 'Sem critérios de aceite nesta história.')
                child_column = child_fields.get('System.BoardColumn', 'Sem Coluna')

                epicos_agrupados[epic_id]["historias"].append({
                    "id": child_id,
                    "titulo": f"[{child_column}] {child_title}",
                    "criterio_aceite": child_crit
                })

                todos_ids_historias_envolvidas.append(child_id)

        epicos_string = ",".join(map(str, epicos_para_processar))
        epic_url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/workitems?ids={epicos_string}&fields=System.Id,Microsoft.VSTS.Common.AcceptanceCriteria&api-version=7.1"

        try:
            epic_response = self._request_with_retry("get", epic_url)
        except RequestException as exc:
            print(f"⚠️ [Azure] Não foi possível buscar os critérios dos épicos: {exc}")
            return epicos_agrupados, todos_ids_historias_envolvidas

        if epic_response.status_code == 200:
            for epic_data in epic_response.json().get('value', []):
                e_id = str(epic_data['id'])
                criterio = epic_data['fields'].get('Microsoft.VSTS.Common.AcceptanceCriteria', 'Sem critérios no Épico.')
                if e_id in epicos_agrupados:
                    epicos_agrupados[e_id]["criterio_epic"] = criterio

        return epicos_agrupados, todos_ids_historias_envolvidas