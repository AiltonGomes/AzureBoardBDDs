import sys
from services.azure_service import AzureService
from services.gemini_service import GeminiService
from services.file_service import FileService

def executor_principal():
    print("==========================================================")
    print("🚀 INICIANDO GERADOR AUTOMÁTICO DE BDD (LOGICA AMPLIADA) 🚀")
    print("==========================================================\n")

    azure = AzureService()
    gemini = GeminiService()
    file_system = FileService()

    # 1. Executa a busca mapeando Épicos através da coluna e capturando a árvore completa de histórias
    epicos_agrupados, ids_para_arquivar = azure.buscar_historias_novas_sortimento()

    if epicos_agrupados is None:
        print("❌ Abortando execução devido a falhas na API do Azure.")
        sys.exit(1)

    if not epicos_agrupados:
        print("\n✨ [Board] Nenhuma história NOVA disparou o gatilho na coluna 'Aguardando Dev' hoje. Tudo atualizado!")
        sys.exit(0)

    print(f"\n🔥 Preparando relatórios para {len(epicos_agrupados)} Bloco(s) de Épico(s) Expandido(s).")

    # 2. Varre os blocos consolidados
    for epic_id, conteudo in epicos_agrupados.items():
        print(f"\n----------------------------------------------------------")
        print(f"📦 Processando Bloco Ampliado do Épico ID: #{epic_id}")
        print(f"----------------------------------------------------------")
        
        bloco_criterios = f"--- CRITÉRIOS DO ÉPICO PAI (# {epic_id}) ---\n{conteudo['criterio_epic']}\n\n"
        bloco_criterios += "--- CRITÉRIOS DE TODAS AS HISTÓRIAS DO ÉPICO ---\n"
        
        for h in conteudo['historias']:
            print(f"  └─► Compilando Requisitos da História #{h['id']} - {h['titulo']}")
            bloco_criterios += f"\n🔹 História #{h['id']} {h['titulo']}:\n{h['criterio_aceite']}\n"

        # 3. O Gemini lê os critérios unificados da árvore do Épico e cria a Feature Completa
        conteudo_bdd = gemini.gerar_bdd(epic_id, bloco_criterios)

        if conteudo_bdd:
            # 4. Grava o arquivo físico {ID_DO_EPICO}.feature
            file_system.salvar_feature(epic_id, conteudo_bdd)
        else:
            print(f"❌ Não foi possível gerar o BDD para o Épico #{epic_id} devido a falhas no modelo.")

    # 5. Adiciona permanentemente TODAS as histórias envolvidas no arquivo JSON histórico
    # Isso garante que se uma história irmã estava em 'In Dev', ela não vai disparar o processo de novo
    historico_atual = azure.carregar_historico()
    historico_atualizado = list(set(historico_atual + ids_para_arquivar))
    azure.salvar_historico(historico_atualizado)
    
    print("\n==========================================================")
    print("✅ EXECUÇÃO CONCLUÍDA! RELATÓRIO AMPLIADO E HISTÓRICO ATUALIZADO.")
    print("==========================================================")

if __name__ == "__main__":
    executor_principal()