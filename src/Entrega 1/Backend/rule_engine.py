import angle_calculator

def evaluate_stroke(stroke_class_id, landmarks):
    """
    Avalia a biomecânica do golpe baseando-se nos ângulos articulares.
    0 = Forehand, 1 = Backhand, 2 = Saque.
    Retorna uma string de feedback, um dicionário de ângulos e uma lista de juntas com erro.
    """
    feedback = []
    angles = {}
    failed_joints = []
    
    # Assumindo jogador destro para as regras base.
    # Em um sistema completo, isso seria configurável.
    
    if stroke_class_id == 0:  # Forehand
        elbow_angle = angle_calculator.get_elbow_angle(landmarks, side='right')
        angles['elbow_r'] = elbow_angle
        
        if elbow_angle < 120:
            feedback.append("Cotovelo muito flexionado no impacto")
            failed_joints.append("cotovelo_dir")
        else:
            feedback.append("Boa extensão do braço")
            
    elif stroke_class_id == 1:  # Backhand
        elbow_angle_l = angle_calculator.get_elbow_angle(landmarks, side='left')
        angles['elbow_l'] = elbow_angle_l
        
        if elbow_angle_l < 110:
            feedback.append("Cotovelo esquerdo muito flexionado")
            failed_joints.append("cotovelo_esq")
        else:
            feedback.append("Braço firme no backhand")
            
    elif stroke_class_id == 2:  # Saque
        knee_angle_r = angle_calculator.get_knee_angle(landmarks, side='right')
        knee_angle_l = angle_calculator.get_knee_angle(landmarks, side='left')
        angles['knee_r'] = knee_angle_r
        angles['knee_l'] = knee_angle_l
        
        # Considera a flexão de ambos os joelhos para o saque
        avg_knee = (knee_angle_r + knee_angle_l) / 2
        if avg_knee > 150:
            feedback.append("Dobre mais os joelhos (flexão pobre)")
            failed_joints.extend(["joelho_dir", "joelho_esq"])
        else:
            feedback.append("Boa flexão para impulsão do saque")
            
    else:
        feedback.append("Aguardando golpe válido...")
        
    return " | ".join(feedback), angles, failed_joints
