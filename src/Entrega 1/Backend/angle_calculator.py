import numpy as np

def calculate_angle(a, b, c):
    """
    Calcula o ângulo em graus entre 3 pontos (x, y, z) onde 'b' é o vértice.
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    ba = a - b
    bc = c - b
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    
    return np.degrees(angle)

def get_landmark_coord(landmark):
    """Extrai [x, y, z] do objeto landmark do MediaPipe Tasks API."""
    return [landmark.x, landmark.y, landmark.z]

def get_elbow_angle(landmarks, side='right'):
    """Calcula o ângulo do cotovelo."""
    # MediaPipe IDs: 
    # Esquerdo: Ombro (11), Cotovelo (13), Pulso (15)
    # Direito: Ombro (12), Cotovelo (14), Pulso (16)
    if side == 'right':
        a = get_landmark_coord(landmarks[12])
        b = get_landmark_coord(landmarks[14])
        c = get_landmark_coord(landmarks[16])
    else:
        a = get_landmark_coord(landmarks[11])
        b = get_landmark_coord(landmarks[13])
        c = get_landmark_coord(landmarks[15])
    return calculate_angle(a, b, c)

def get_knee_angle(landmarks, side='right'):
    """Calcula o ângulo do joelho."""
    # MediaPipe IDs:
    # Esquerdo: Quadril (23), Joelho (25), Tornozelo (27)
    # Direito: Quadril (24), Joelho (26), Tornozelo (28)
    if side == 'right':
        a = get_landmark_coord(landmarks[24])
        b = get_landmark_coord(landmarks[26])
        c = get_landmark_coord(landmarks[28])
    else:
        a = get_landmark_coord(landmarks[23])
        b = get_landmark_coord(landmarks[25])
        c = get_landmark_coord(landmarks[27])
    return calculate_angle(a, b, c)
