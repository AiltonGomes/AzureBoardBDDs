import json
import re

from google import genai
from google.genai import types
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, PROMPT_SISTEMA_BDD


class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.config = types.GenerateContentConfig(
            system_instruction=PROMPT_SISTEMA_BDD,
            temperature=0.2
        )

    def _normalizar_conteudo_gherkin(self, conteudo):
        if not conteudo:
            return None

        texto = conteudo.strip()

        if texto.startswith("```"):
            texto = re.sub(r"^```(?:gherkin|plaintext|text)?\s*", "", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\s*```$", "", texto, flags=re.IGNORECASE).strip()

        if texto.startswith("{"):
            try:
                payload = json.loads(texto)
                funcionalidade = payload.get("funcionalidade", "Funcionalidade")
                cenarios = payload.get("cenarios", [])

                linhas = [f"Funcionalidade: {funcionalidade}", ""]
                for cenario in cenarios:
                    nome = cenario.get("nome_cenario", "Cenário sem nome")
                    gherkin = cenario.get("gherkin_puro") or cenario.get("gherkin") or ""
                    if gherkin:
                        linhas.append(f"  Cenário: {nome}")
                        linhas.extend([f"    {linha}" for linha in gherkin.splitlines() if linha.strip()])
                        linhas.append("")

                texto = "\n".join(linhas).strip()
            except json.JSONDecodeError:
                pass

        if not texto.startswith("Funcionalidade:"):
            texto = f"Funcionalidade: Funcionalidade gerada automaticamente\n\n{texto}"

        return texto

    def gerar_bdd(self, epic_id, criterios_consolidados):
        prompt_usuario = f"""
        Gere um arquivo .feature com BDD em Gherkin para o épico ID #{epic_id}.
        Considere os seguintes critérios de aceite coletados das histórias e do próprio épico:

        {criterios_consolidados}
        """

        try:
            print(f"🤖 [Gemini] Processando critérios e gerando BDD para o Épico {epic_id}...")
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt_usuario,
                config=self.config
            )
            return self._normalizar_conteudo_gherkin(response.text)
        except Exception as e:
            print(f"❌ Erro ao chamar a API do Gemini: {e}")
            return None