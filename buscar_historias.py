import requests
from requests.auth import HTTPBasicAuth
import json
import os

# 1. Configurações de Acesso Reais
ORGANIZATION =  os.getenv("AZURE_ORGANIZATION")
PROJECT =       os.getenv("AZURE_PROJECT")
PAT =           os.getenv("AZURE_PAT")

auth = HTTPBasicAuth('', PAT)
headers = {'Content-Type': 'application/json'}

ARQUIVO_HISTORICO = "historias_processadas.json"

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, 'r') as f:
            return json.load(f)
    return []

def salvar_historico(historico):
    with open(ARQUIVO_HISTORICO, 'w') as f:
        json.dump(historico, f, indent=4)

# 2. Query Ampla: Busca TUDO que está na coluna 'Aguardando Dev' do projeto
wiql_url = f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/wit/wiql?api-version=7.1"
query_wiql = {
    "query": """
        SELECT [System.Id] 
        FROM WorkItems 
        WHERE [System.TeamProject] = 'Tech' 
          AND [System.WorkItemType] = 'User Story' 
          AND [System.BoardColumn] = 'Aguardando Dev'
    """
}

print("Conectando à API e trazendo dados gerais da coluna 'Aguardando Dev'...")
response = requests.post(wiql_url, json=query_wiql, auth=auth, headers=headers)

if response.status_code == 200:
    items = response.json().get('workItems', [])
    ids_totais = [item['id'] for item in items]
    
    if not ids_totais:
        print("Nenhuma história encontrada na coluna 'Aguardando Dev' no projeto.")
        exit()
        
    # 3. Buscar os detalhes de todos os itens da coluna para filtrar o Sortimento via código
    print(f"Analisando os cards da coluna em segundo plano... (Total de cards: {len(ids_totais)})")
    ids_string = ",".join(map(str, ids_totais))
    details_url = f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/wit/workitems?ids={ids_string}&$expand=relations&api-version=7.1"
    details_response = requests.get(details_url, auth=auth)
    
    if details_response.status_code == 200:
        detalhes_historias = details_response.json().get('value', [])
        
        # Carrega histórico para saber o que é novo
        historico_antigo = carregar_historico()
        
        epicos_agrupados = {}
        novos_ids_processados = []
        
        for story in detalhes_historias:
            fields = story['fields']
            area_path = fields.get('System.AreaPath', '')
            
            # FILTRO CIRÚRGICO EM MEMÓRIA: Só queremos o que for do Sortimento Dinâmico
            if "Dynamic_Assortment_Services" not in area_path:
                continue
                
            story_id = story['id']
            
            # Se a história do Sortimento já foi processada antes, pula ela
            if story_id in historico_antigo:
                continue
                
            title = fields.get('System.Title', '')
            crit_story = fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', 'Sem critérios na história.')
            
            # Registra que estamos tratando este ID novo
            novos_ids_processados.append(story_id)
            
            # Caçar o ID do Épico (Parent)
            epic_id = "Sem_Epico_Vinculado"
            relations = story.get('relations', [])
            for rel in relations:
                if rel['rel'] == 'System.LinkTypes.Hierarchy-Reverse':
                    epic_id = rel['url'].split('/')[-1]
                    break
            
            dados_historia = {
                "id": story_id,
                "titulo": title,
                "criterio_aceite": crit_story
            }
            
            if epic_id not in epicos_agrupados:
                epicos_agrupados[epic_id] = []
            epicos_agrupados[epic_id].append(dados_historia)
            
        # 4. Validar se encontramos algo novo do SD
        if not epicos_agrupados:
            print("\n[!] Nenhuma história NOVA do Sortimento foi encontrada para processamento nesta rodada.")
            exit()
            
        print("\n=== MAPEAMENTO DE HISTÓRIAS NOVAS E SEUS ÉPICOS PAI (SORTIMENTO) ===")
        for epic_id, historias in epicos_agrupados.items():
            print(f"\n📌 ÉPICO PARENT ID: {epic_id}")
            for h in historias:
                print(f"  └─► História ID: {h['id']} | Título: {h['titulo']}")
        
        # 5. Atualizar o histórico local para a próxima execução
        historico_atualizado = list(set(historico_antigo + novos_ids_processados))
        salvar_historico(historico_atualizado)
        print("\n[OK] Histórico local atualizado com sucesso no arquivo JSON.")
        
    else:
        print(f"Erro ao buscar detalhes: {details_response.text}")
else:
    print(f"Erro na query: {response.status_code} - {response.text}")