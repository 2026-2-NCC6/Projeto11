import numpy as np
import angle_calculator

def evaluate_stroke(stroke_class_id, landmarks, lateralidade='destro'):
    """
    Avaliação de frame único (mantida para compatibilidade direta de telemetria em tempo real).
    """
    feedback = []
    angles = {}
    failed_joints = []
    
    is_left_handed = (str(lateralidade).lower() == 'canhoto')
    dom_arm = 'left' if is_left_handed else 'right'
    non_dom_arm = 'right' if is_left_handed else 'left'
    dom_joint_name = "cotovelo_esq" if is_left_handed else "cotovelo_dir"
    non_dom_joint_name = "cotovelo_dir" if is_left_handed else "cotovelo_esq"

    quality_score = 0.0
    grade = "NONE"

    if stroke_class_id == 0:  # Forehand
        elbow_angle = angle_calculator.get_elbow_angle(landmarks, side=dom_arm)
        shoulder_angle = angle_calculator.get_shoulder_angle(landmarks, side=dom_arm)
        angle_key = 'elbow_r' if not is_left_handed else 'elbow_l'
        angles[angle_key] = round(elbow_angle, 1)
        angles['shoulder'] = round(shoulder_angle, 1)
        
        if elbow_angle < 120:
            feedback.append("Cotovelo muito flexionado no impacto")
            failed_joints.append(dom_joint_name)
            grade = "FAULT"
            quality_score = 0.0
        elif elbow_angle > 175:
            feedback.append("Braço excessivamente rígido/esticado")
            failed_joints.append(dom_joint_name)
            grade = "FAULT"
            quality_score = 0.2
        else:
            if 135 <= elbow_angle <= 165:
                feedback.append("Excelente extensão de braço")
                grade = "PERFECT"
                quality_score = 1.0
            else:
                feedback.append("Boa extensão do braço")
                grade = "GOOD"
                quality_score = 0.85
            
    elif stroke_class_id == 1:  # Backhand
        elbow_angle = angle_calculator.get_elbow_angle(landmarks, side=dom_arm)
        angle_key = 'elbow_r' if not is_left_handed else 'elbow_l'
        angles[angle_key] = round(elbow_angle, 1)
        
        if elbow_angle < 110:
            feedback.append("Cotovelo muito encolhido no backhand")
            failed_joints.append(dom_joint_name)
            grade = "FAULT"
            quality_score = 0.0
        else:
            if 130 <= elbow_angle <= 165:
                feedback.append("Braço firme e amplitude ideal")
                grade = "PERFECT"
                quality_score = 1.0
            else:
                feedback.append("Braço firme no backhand")
                grade = "GOOD"
                quality_score = 0.85
            
    elif stroke_class_id == 2:  # Saque
        knee_angle_r = angle_calculator.get_knee_angle(landmarks, side='right')
        knee_angle_l = angle_calculator.get_knee_angle(landmarks, side='left')
        elbow_angle = angle_calculator.get_elbow_angle(landmarks, side=dom_arm)
        angles['knee_r'] = round(knee_angle_r, 1)
        angles['knee_l'] = round(knee_angle_l, 1)
        angles['elbow'] = round(elbow_angle, 1)
        
        avg_knee = (knee_angle_r + knee_angle_l) / 2.0
        if avg_knee > 155:
            feedback.append("Dobre mais os joelhos para impulsão")
            failed_joints.extend(["joelho_dir", "joelho_esq"])
            grade = "FAULT"
            quality_score = 0.0
        else:
            if 105 <= avg_knee <= 135 and elbow_angle >= 140:
                feedback.append("Impulsão de joelho e extensão perfeitas")
                grade = "PERFECT"
                quality_score = 1.0
            else:
                feedback.append("Boa flexão e alcance no saque")
                grade = "GOOD"
                quality_score = 0.85
            
    else:
        feedback.append("Aguardando golpe...")
        grade = "NONE"
        quality_score = 0.0
        
    return " | ".join(feedback), angles, failed_joints, quality_score, grade


def evaluate_stroke_trajectory(stroke_class_id, trajectory_landmarks, lateralidade='destro'):
    """
    Avaliação Contínua de Toda a Trajetória (Sequência temporal dos 5 segundos de replay).
    Examina preparação, aceleração, ponto de impacto e terminação (follow-through).
    Retorna:
    (feedback_str, angles_dict, failed_joints, quality_score, grade, worst_frame_idx)
    """
    if not trajectory_landmarks or len(trajectory_landmarks) < 5:
        return "Movimento muito curto para análise", {}, [], 0.0, "NONE", 0

    is_left_handed = (str(lateralidade).lower() == 'canhoto')
    dom_arm = 'left' if is_left_handed else 'right'
    dom_joint_elbow = "cotovelo_esq" if is_left_handed else "cotovelo_dir"
    dom_joint_wrist = "pulso_esq" if is_left_handed else "pulso_dir"
    dom_joint_shoulder = "ombro_esq" if is_left_handed else "ombro_dir"

    feedback_list = []
    failed_joints = set()
    worst_frame_idx = 0
    worst_severity = 0.0

    n_frames = len(trajectory_landmarks)
    
    # Encontra o momento de ápice de aceleração do punho (ponto de impacto provável)
    wrist_idx = 15 if is_left_handed else 16
    wrist_speeds = []
    for t in range(1, n_frames):
        c_prev = angle_calculator.get_landmark_coord(trajectory_landmarks[t-1][wrist_idx])
        c_curr = angle_calculator.get_landmark_coord(trajectory_landmarks[t][wrist_idx])
        speed = np.linalg.norm(np.array(c_curr[:2]) - np.array(c_prev[:2]))
        wrist_speeds.append(speed)

    impact_idx = int(np.argmax(wrist_speeds)) if wrist_speeds else n_frames // 2

    # Amostragem das fases:
    prep_phase = trajectory_landmarks[:max(1, impact_idx - 5)]
    impact_frame = trajectory_landmarks[impact_idx]
    follow_phase = trajectory_landmarks[min(n_frames - 1, impact_idx + 5):]

    angles_summary = {}

    if stroke_class_id == 0:  # FOREHAND
        # 1. Rastreamento contínuo do cotovelo dominante ao longo de todo o swing
        min_elbow = 180.0
        min_elbow_frame = impact_idx
        for idx_f, lms in enumerate(trajectory_landmarks):
            elb = angle_calculator.get_elbow_angle(lms, side=dom_arm)
            if elb < min_elbow:
                min_elbow = elb
                min_elbow_frame = idx_f

        angles_summary['elbow_min'] = round(min_elbow, 1)
        angles_summary['elbow_impact'] = round(angle_calculator.get_elbow_angle(impact_frame, side=dom_arm), 1)

        if min_elbow < 118:
            feedback_list.append(f"Cotovelo muito encolhido durante o swing ({min_elbow:.0f}°)")
            failed_joints.add(dom_joint_elbow)
            worst_frame_idx = min_elbow_frame
            worst_severity = max(worst_severity, 1.0)
        elif min_elbow > 175:
            feedback_list.append("Braço rígido demais, relaxe o cotovelo")
            failed_joints.add(dom_joint_elbow)
            worst_frame_idx = min_elbow_frame
            worst_severity = max(worst_severity, 0.7)

        # 2. Rotação do tronco
        max_rotation = max([angle_calculator.get_torso_rotation_angle(lms) for lms in trajectory_landmarks] or [0])
        angles_summary['torso_rot_max'] = round(max_rotation, 1)
        if max_rotation < 16.0:
            feedback_list.append("Faltou rotação de tronco no golpe")
            failed_joints.add(dom_joint_shoulder)
            worst_severity = max(worst_severity, 0.6)

        # 3. Terminação (Follow-through alto)
        # O punho no follow_phase deve subir acima da linha dos ombros
        if follow_phase:
            final_lms = follow_phase[-1]
            wrist_y = angle_calculator.get_landmark_coord(final_lms[wrist_idx])[1]
            opp_sh_idx = 12 if is_left_handed else 11
            opp_sh_y = angle_calculator.get_landmark_coord(final_lms[opp_sh_idx])[1]
            # Em coordenadas de imagem, y menor = mais alto
            if wrist_y > (opp_sh_y + 0.12):
                feedback_list.append("Terminação baixa, finalize por cima do ombro")
                failed_joints.add(dom_joint_wrist)
                worst_severity = max(worst_severity, 0.5)

    elif stroke_class_id == 1:  # BACKHAND
        min_elbow = 180.0
        min_elbow_frame = impact_idx
        for idx_f, lms in enumerate(trajectory_landmarks):
            elb = angle_calculator.get_elbow_angle(lms, side=dom_arm)
            if elb < min_elbow:
                min_elbow = elb
                min_elbow_frame = idx_f

        angles_summary['elbow_min'] = round(min_elbow, 1)
        if min_elbow < 112:
            feedback_list.append(f"Cotovelo encolhido no backhand ({min_elbow:.0f}°)")
            failed_joints.add(dom_joint_elbow)
            worst_frame_idx = min_elbow_frame
            worst_severity = max(worst_severity, 1.0)

        # Elevação de ombro
        sh_angle = angle_calculator.get_shoulder_angle(impact_frame, side=dom_arm)
        angles_summary['shoulder_impact'] = round(sh_angle, 1)
        if sh_angle < 35:
            feedback_list.append("Abra mais o braço no backhand")
            failed_joints.add(dom_joint_shoulder)
            worst_severity = max(worst_severity, 0.6)

    elif stroke_class_id == 2:  # SAQUE
        # 1. Flexão de joelhos na fase de preparação (deve agachar para saltar)
        min_knee = 180.0
        min_knee_frame = 0
        for idx_f, lms in enumerate(trajectory_landmarks[:max(1, impact_idx)]):
            kr = angle_calculator.get_knee_angle(lms, side='right')
            kl = angle_calculator.get_knee_angle(lms, side='left')
            avg_k = (kr + kl) / 2.0
            if avg_k < min_knee:
                min_knee = avg_k
                min_knee_frame = idx_f

        angles_summary['knee_flex_prep'] = round(min_knee, 1)
        if min_knee > 152:
            feedback_list.append("Dobre mais os joelhos na preparação do saque")
            failed_joints.add("joelho_dir")
            failed_joints.add("joelho_esq")
            worst_frame_idx = min_knee_frame
            worst_severity = max(worst_severity, 0.8)

        # 2. Extensão máxima no ponto mais alto (impacto)
        elbow_impact = angle_calculator.get_elbow_angle(impact_frame, side=dom_arm)
        angles_summary['elbow_impact'] = round(elbow_impact, 1)
        if elbow_impact < 135:
            feedback_list.append("Estenda o braço mais no alto ao golpear")
            failed_joints.add(dom_joint_elbow)
            worst_severity = max(worst_severity, 0.9)

    # Classificação Final de Qualidade:
    failed_list = sorted(list(failed_joints))
    if len(failed_list) == 0:
        grade = "PERFECT"
        quality_score = 1.0
        feedback_str = "Movimento impecável em toda a trajetória!"
    elif worst_severity <= 0.6 and len(failed_list) == 1:
        grade = "GOOD"
        quality_score = 0.85
        feedback_str = f"Bom golpe. Ajuste sugerido: {feedback_list[0]}"
    else:
        grade = "FAULT"
        quality_score = max(0.0, 0.60 - worst_severity * 0.4)
        feedback_str = f"Ajuste necessário: {' | '.join(feedback_list)}"

    return feedback_str, angles_summary, failed_list, quality_score, grade, worst_frame_idx
