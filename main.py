import argparse
import sys
import logging
from services.azure_service import AzureService
from services.gemini_service import GeminiService
from services.file_service import FileService

# Configuração de Logs para o roteador
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def gerar_cenarios_colunas(azure, ia_service, file_system):
    """
    Varre as colunas monitoradas no Azure, encontra novas histórias,
    monta a árvore do Épico e pede para a IA gerar o BDD.
    """
    print("==========================================================")
    print("🚀 INICIANDO GERADOR AUTOMÁTICO DE BDD (LOGICA AMPLIADA) 🚀")
    print("==========================================================\n")
    
    # 1. Executa a busca mapeando Épicos através da coluna e capturando a árvore completa de histórias
    epicos_agrupados, ids_para_arquivar = azure.buscar_historias_novas_sortimento()

    if epicos_agrupados is None:
        print("❌ Abortando execução devido a falhas na API do Azure.")
        sys.exit(1)

    if not epicos_agrupados:
        print("\n✨ [Board] Nenhuma história NOVA disparou o gatilho nas colunas monitoradas hoje. Tudo atualizado!")
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
        conteudo_bdd = ia_service.gerar_bdd(epic_id, bloco_criterios)

        if conteudo_bdd:
            # 4. Grava o arquivo físico {ID_DO_EPICO}.feature
            file_system.salvar_feature(epic_id, conteudo_bdd)
        else:
            print(f"❌ Não foi possível gerar o BDD para o Épico #{epic_id} devido a falhas no modelo.")

    # 5. Adiciona permanentemente TODAS as histórias envolvidas no arquivo JSON histórico
    historico_atual = azure.carregar_historico()
    historico_atualizado = list(set(historico_atual + ids_para_arquivar))
    azure.salvar_historico(historico_atualizado)
    
    print("\n==========================================================")
    print("✅ EXECUÇÃO CONCLUÍDA! RELATÓRIO AMPLIADO E HISTÓRICO ATUALIZADO.")
    print("==========================================================")


def main():
    parser = argparse.ArgumentParser(description="Orquestrador da Automação Azure Boards")
    
    parser.add_argument("--ia", choices=["copilot", "gemini"], default="gemini", 
                        help="Escolha qual IA processará as histórias (Padrão: gemini)")
    
    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponíveis")

    # --- Comando: GERAR ---
    parser_gerar = subparsers.add_parser("gerar", help="Gera cenários BDD a partir do Azure")
    parser_gerar.add_argument("--origem", choices=["colunas", "epico"], required=True, 
                              help="Buscar histórias nas colunas ou direto em um Épico?")
    parser_gerar.add_argument("--id", type=int, help="ID do Épico (obrigatório se --origem for epico)")

    # Lê os argumentos digitados
    args = parser.parse_args()

    # Se o usuário digitou apenas "py main.py", injetamos o comando padrão!
    if len(sys.argv) == 1:
        logger.info("Nenhum comando informado. Assumindo fluxo padrão: Gerar BDD pelas colunas.")
        args = parser.parse_args(["gerar", "--origem", "colunas"])

    # Instanciando serviços
    azure = AzureService()
    file_system = FileService()
    
    # Lógica para instanciar a IA
    if args.ia == "gemini":
        ia_service = GeminiService()
    else:
        print("❌ Serviço do Copilot ainda não foi implementado. Use o Gemini por enquanto.")
        sys.exit(1)

    # ==========================================
    # ROTEAMENTO
    # ==========================================
    if args.comando == "gerar":
        if args.origem == "colunas":
            gerar_cenarios_colunas(azure, ia_service, file_system)
            
        elif args.origem == "epico":
            if not args.id:
                print("❌ Erro: Para gerar por épico, você deve fornecer o parâmetro --id.")
                sys.exit(1)
            print(f"🚀 Iniciando geração focada no Épico #{args.id}...")
            # TODO: Aqui entrará o método gerar_cenarios_epico no Passo 2

if __name__ == "__main__":
    main()