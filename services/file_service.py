import os

class FileService:
    def __init__(self, output_dir="features"):
        self.output_dir = output_dir
        # Garante que a pasta 'features' existe no projeto
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def salvar_feature(self, epic_id, conteudo_bdd):
        """
        Cria um arquivo {epic_id}.feature com os cenários BDD gerados.
        """
        nome_arquivo = f"{epic_id}.feature"
        caminho_completo = os.path.join(self.output_dir, nome_arquivo)
        
        try:
            with open(caminho_completo, "w", encoding="utf-8") as f:
                f.write(conteudo_bdd)
            print(f"💾 [Arquivo] Arquivo criado com sucesso: {caminho_completo}")
            return caminho_completo
        except Exception as e:
            print(f"❌ Erro ao salvar o arquivo .feature: {e}")
            return None