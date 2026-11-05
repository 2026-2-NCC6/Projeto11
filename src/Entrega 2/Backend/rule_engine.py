import angle_calculator

def evaluate_stroke(stroke_class_id, landmarks, lateralidade='destro'):
    """
    Avalia a biomecânica do golpe baseando-se nos ângulos articulares.
    0 = Forehand, 1 = Backhand, 2 = Saque.
    lateralidade: 'destro' ou 'canhoto' (US07).
    Retorna uma tupla de 5 elementos:
    (feedback_str, angles_dict, failed_joints, quality_score, grade)
    onde:
      - quality_score: float de 0.0 a 1.0
      - grade: "PERFECT", "GOOD", "FAULT" ou "NONE"
    """
    feedback = []
    angles = {}
    failed_joints = []
    
    is_left_handed = (lateralidade.lower() == 'canhoto')
    dom_arm = 'left' if is_left_handed else 'right'
    non_dom_arm = 'right' if is_left_handed else 'left'
    dom_joint_name = "cotovelo_esq" if is_left_handed else "cotovelo_dir"
    non_dom_joint_name = "cotovelo_dir" if is_left_handed else "cotovelo_esq"

    quality_score = 0.0
    grade = "NONE"

    if stroke_class_id == 0:  # Forehand
        elbow_angle = angle_calculator.get_elbow_angle(landmarks, side=dom_arm)
        angle_key = 'elbow_r' if not is_left_handed else 'elbow_l'
        angles[angle_key] = elbow_angle
        
        if elbow_angle < 120:
            feedback.append("Cotovelo muito flexionado no impacto")
            failed_joints.append(dom_joint_name)
            grade = "FAULT"
            quality_score = 0.0
        else:
            feedback.append("Boa extensão do braço")
            if 135 <= elbow_angle <= 165:
                grade = "PERFECT"
                quality_score = 1.0
            else:
                grade = "GOOD"
                quality_score = 0.85
            
    elif stroke_class_id == 1:  # Backhand
        elbow_angle = angle_calculator.get_elbow_angle(landmarks, side=non_dom_arm)
        angle_key = 'elbow_l' if not is_left_handed else 'elbow_r'
        angles[angle_key] = elbow_angle
        
        if elbow_angle < 110:
            feedback.append("Cotovelo muito flexionado no backhand")
            failed_joints.append(non_dom_joint_name)
            grade = "FAULT"
            quality_score = 0.0
        else:
            feedback.append("Braço firme no backhand")
            if 130 <= elbow_angle <= 160:
                grade = "PERFECT"
                quality_score = 1.0
            else:
                grade = "GOOD"
                quality_score = 0.85
            
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
            grade = "FAULT"
            quality_score = 0.0
        else:
            feedback.append("Boa flexão para impulsão do saque")
            if 105 <= avg_knee <= 135:
                grade = "PERFECT"
                quality_score = 1.0
            else:
                grade = "GOOD"
                quality_score = 0.85
            
    else:
        feedback.append("Aguardando golpe válido...")
        grade = "NONE"
        quality_score = 0.0
        
    return " | ".join(feedback), angles, failed_joints, quality_score, grade
