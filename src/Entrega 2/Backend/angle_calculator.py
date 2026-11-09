import numpy as np

def calculate_angle(a, b, c):
    """
    Calcula o ângulo em graus entre 3 pontos (x, y, z) onde 'b' é o vértice.
    """
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    c = np.array(c, dtype=np.float32)
    
    ba = a - b
    bc = c - b
    
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return 180.0
        
    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    
    return float(np.degrees(angle))

def get_landmark_coord(landmark):
    """Extrai [x, y, z] do objeto landmark do MediaPipe Tasks API ou de dicionário/lista."""
    if hasattr(landmark, 'x'):
        return [landmark.x, landmark.y, landmark.z]
    elif isinstance(landmark, (list, tuple, np.ndarray)):
        return [float(landmark[0]), float(landmark[1]), float(landmark[2]) if len(landmark) > 2 else 0.0]
    return [0.0, 0.0, 0.0]

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

def get_shoulder_angle(landmarks, side='right'):
    """Calcula o ângulo de elevação do ombro (Quadril -> Ombro -> Cotovelo)."""
    # Direito: Quadril (24), Ombro (12), Cotovelo (14)
    # Esquerdo: Quadril (23), Ombro (11), Cotovelo (13)
    if side == 'right':
        a = get_landmark_coord(landmarks[24])
        b = get_landmark_coord(landmarks[12])
        c = get_landmark_coord(landmarks[14])
    else:
        a = get_landmark_coord(landmarks[23])
        b = get_landmark_coord(landmarks[11])
        c = get_landmark_coord(landmarks[13])
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

def get_torso_rotation_angle(landmarks):
    """
    Calcula a rotação dos ombros em relação aos quadris no plano transversal (X-Z).
    Retorna o ângulo em graus (0° = alinhados, >20° = tronco rotacionado).
    """
    sh_l = np.array(get_landmark_coord(landmarks[11]))
    sh_r = np.array(get_landmark_coord(landmarks[12]))
    hip_l = np.array(get_landmark_coord(landmarks[23]))
    hip_r = np.array(get_landmark_coord(landmarks[24]))

    # Vetores no plano X-Z
    vec_shoulders = np.array([sh_l[0] - sh_r[0], sh_l[2] - sh_r[2]])
    vec_hips = np.array([hip_l[0] - hip_r[0], hip_l[2] - hip_r[2]])

    norm_s = np.linalg.norm(vec_shoulders)
    norm_h = np.linalg.norm(vec_hips)
    if norm_s < 1e-4 or norm_h < 1e-4:
        return 0.0

    dot = np.dot(vec_shoulders, vec_hips) / (norm_s * norm_h)
    angle = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))
    return float(angle)
