import numpy as np

class TennisTransformerGPU:
    def __init__(self):
        """
        Mock class to represent the TennisTransformerGPU model described in prompt_contexto.md.
        In a real scenario, this would load weights into the GPU via PyTorch/ONNX.
        """
        print("TennisTransformerGPU: Modelo (Mock) carregado na memória.")
        
    def __call__(self, input_tensor):
        """
        Recebe um tensor de shape (Batch, Frames, Landmarks, Coords) -> (1, 60, 33, 3)
        Retorna (class_id, confidence)
        class_id: 0 = Forehand, 1 = Backhand, 2 = Saque, 3 = Repouso
        """
        # Verifica o shape (apenas por segurança e debugging)
        # expected shape: (1, 60, 33, 3)
        # Vamos gerar predições aleatórias ou estáticas de mock para teste visual.
        
        # Simula uma chance aleatória de detectar um forehand com alta confiança
        chance = np.random.rand()
        if chance > 0.95:
            # 5% de chance de detectar um Saque
            return 2, 0.92
        elif chance > 0.90:
            # 5% de chance de detectar um Forehand
            return 0, 0.88
        else:
            # 90% de chance de estar em repouso
            return 3, 0.99
            
    def to(self, device):
        """Mock method for moving to GPU"""
        print(f"TennisTransformerGPU: Movido para {device}")
        return self
