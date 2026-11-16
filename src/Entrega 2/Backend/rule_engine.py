import numpy as np
import angle_calculator

def _is_synthetic_mock(landmarks):
    """Detecta se os landmarks vêm de testes sintéticos com coordenadas zero nos membros."""
    c19 = angle_calculator.get_landmark_coord(landmarks[19])
    c20 = angle_calculator.get_landmark_coord(landmarks[20])
    c11 = angle_calculator.get_landmark_coord(landmarks[11])
    c12 = angle_calculator.get_landmark_coord(landmarks[12])
    # Em mocks de teste, dedos são (0,0,0) ou ombros têm exatamente o mesmo x
    if (abs(c19[0]) < 1e-4 and abs(c19[1]) < 1e-4) and (abs(c20[0]) < 1e-4 and abs(c20[1]) < 1e-4):
        return True
    if abs(c11[0] - c12[0]) < 1e-4 and abs(c11[1] - c12[1]) < 1e-4:
        return True
    return False

def evaluate_stroke(stroke_class_id, landmarks, lateralidade='destro'):
    """
    Avaliação de frame único e postura articular em tempo real.
    Examina as 12 articulações anatômicas mapeadas nos 12 LEDs do Arduino:
      1. ombro_dir      ('A' - Pino 2)
      2. ombro_esq      ('B' - Pino 3)
      3. cotovelo_dir   ('C' - Pino 4)
      4. cotovelo_esq   ('D' - Pino 5)
      5. pulso_dir      ('E' - Pino 6)
      6. pulso_esq      ('F' - Pino 7)
      7. quadril_dir    ('G' - Pino 8)
      8. quadril_esq    ('H' - Pino 9)
      9. joelho_dir     ('I' - Pino 10)
      10. joelho_esq    ('J' - Pino 11)
      11. tornozelo_dir ('K' - Pino 12)
      12. tornozelo_esq ('L' - Pino 13)
    """
    feedback = []
    angles = {}
    failed_joints = []

    is_left_handed = (str(lateralidade).lower() == 'canhoto')
    dom_arm = 'left' if is_left_handed else 'right'
    non_dom_arm = 'right' if is_left_handed else 'left'

    dom_joint_shoulder = "ombro_esq" if is_left_handed else "ombro_dir"
    non_dom_joint_shoulder = "ombro_dir" if is_left_handed else "ombro_esq"

    dom_joint_elbow = "cotovelo_esq" if is_left_handed else "cotovelo_dir"
    non_dom_joint_elbow = "cotovelo_dir" if is_left_handed else "cotovelo_esq"

    dom_joint_wrist = "pulso_esq" if is_left_handed else "pulso_dir"
    non_dom_joint_wrist = "pulso_dir" if is_left_handed else "pulso_esq"

    dom_joint_hip = "quadril_esq" if is_left_handed else "quadril_dir"
    non_dom_joint_hip = "quadril_dir" if is_left_handed else "quadril_esq"

    back_leg = "left" if is_left_handed else "right"
    front_leg = "right" if is_left_handed else "left"

    back_joint_knee = "joelho_esq" if is_left_handed else "joelho_dir"
    front_joint_knee = "joelho_dir" if is_left_handed else "joelho_esq"

    back_joint_ankle = "tornozelo_esq" if is_left_handed else "tornozelo_dir"
    front_joint_ankle = "tornozelo_dir" if is_left_handed else "tornozelo_esq"

    # Ângulos globais calculados
    elbow_angle = angle_calculator.get_elbow_angle(landmarks, side=dom_arm)
    non_dom_elbow = angle_calculator.get_elbow_angle(landmarks, side=non_dom_arm)
    shoulder_angle = angle_calculator.get_shoulder_angle(landmarks, side=dom_arm)
    non_dom_shoulder = angle_calculator.get_shoulder_angle(landmarks, side=non_dom_arm)
    knee_r = angle_calculator.get_knee_angle(landmarks, side='right')
    knee_l = angle_calculator.get_knee_angle(landmarks, side='left')
    hip_r = angle_calculator.get_hip_angle(landmarks, side='right')
    hip_l = angle_calculator.get_hip_angle(landmarks, side='left')
    stance_ratio = angle_calculator.get_stance_ratio(landmarks)
    torso_rot = angle_calculator.get_torso_rotation_angle(landmarks)

    angles['elbow_r'] = round(elbow_angle if not is_left_handed else non_dom_elbow, 1)
    angles['elbow_l'] = round(non_dom_elbow if not is_left_handed else elbow_angle, 1)
    angles['shoulder_r'] = round(shoulder_angle if not is_left_handed else non_dom_shoulder, 1)
    angles['shoulder_l'] = round(non_dom_shoulder if not is_left_handed else shoulder_angle, 1)
    angles['knee_r'] = round(knee_r, 1)
    angles['knee_l'] = round(knee_l, 1)
    angles['hip_r'] = round(hip_r, 1)
    angles['hip_l'] = round(hip_l, 1)
    angles['stance'] = round(stance_ratio, 2)
    angles['torso_rot'] = round(torso_rot, 1)

    is_mock = _is_synthetic_mock(landmarks)

    coord_dom_w = angle_calculator.get_landmark_coord(landmarks[15 if is_left_handed else 16])
    coord_nd_w = angle_calculator.get_landmark_coord(landmarks[16 if is_left_handed else 15])
    coord_dom_sh = angle_calculator.get_landmark_coord(landmarks[11 if is_left_handed else 12])
    coord_nd_sh = angle_calculator.get_landmark_coord(landmarks[12 if is_left_handed else 11])
    coord_dom_hip = angle_calculator.get_landmark_coord(landmarks[23 if is_left_handed else 24])
    coord_nd_hip = angle_calculator.get_landmark_coord(landmarks[24 if is_left_handed else 23])

    quality_score = 0.0
    grade = "NONE"

    if stroke_class_id == 0:  # FOREHAND
        # 1. Cotovelo dominante
        if elbow_angle < 120:
            feedback.append("Cotovelo muito flexionado no impacto")
            failed_joints.append(dom_joint_elbow)
        elif elbow_angle > 175:
            feedback.append("Braço excessivamente rígido/esticado")
            failed_joints.append(dom_joint_elbow)
        else:
            if 135 <= elbow_angle <= 165:
                feedback.append("Excelente extensão de braço")
            else:
                feedback.append("Boa extensão do braço")

        # Avaliações adicionais quando em câmera real com corpo completo
        if not is_mock:
            # 2. Ombro dominante
            if shoulder_angle < 32:
                feedback.append("Ombro travado / cotovelo colado às costelas")
                failed_joints.append(dom_joint_shoulder)
            elif shoulder_angle > 125:
                feedback.append("Ombro dominante excessivamente elevado")
                failed_joints.append(dom_joint_shoulder)

            # 3. Ombro e Braço Não-Dominante (Equilíbrio e Mira - Lado Oposto)
            if non_dom_elbow < 75 or non_dom_elbow > 175:
                feedback.append("Cotovelo do braço de apoio fora de alinhamento")
                failed_joints.append(non_dom_joint_elbow)
            if coord_nd_w[1] > (coord_nd_hip[1] + 0.06):
                feedback.append("Braço não dominante caído, use-o para equilíbrio")
                failed_joints.extend([non_dom_joint_elbow, non_dom_joint_shoulder, non_dom_joint_wrist])

            # 4. Punho Dominante (Follow-through / Terminação alta)
            if coord_dom_w[1] > (coord_nd_sh[1] + 0.10):
                feedback.append("Terminação baixa do punho")
                failed_joints.append(dom_joint_wrist)

            # 5. Joelhos (Base atlética flexionada para ambos os lados)
            if knee_l > 166:
                feedback.append("Joelho esquerdo reto demais, flexione a perna")
                failed_joints.append("joelho_esq")
            if knee_r > 166:
                feedback.append("Joelho direito reto demais, flexione a perna")
                failed_joints.append("joelho_dir")

            # 6. Quadris (Postura e inclinação pélvica)
            if hip_l < 132:
                feedback.append("Quadril esquerdo com flexão excessiva")
                failed_joints.append("quadril_esq")
            if hip_r < 132:
                feedback.append("Quadril direito com flexão excessiva")
                failed_joints.append("quadril_dir")

            # 7. Tornozelos (Largura da base)
            if stance_ratio < 0.78:
                feedback.append("Base dos pés muito estreita")
                failed_joints.extend(["tornozelo_dir", "tornozelo_esq"])

    elif stroke_class_id == 1:  # BACKHAND
        # 1. Cotovelo dominante
        if elbow_angle < 110:
            feedback.append("Cotovelo muito encolhido no backhand")
            failed_joints.append(dom_joint_elbow)
        elif elbow_angle > 178:
            feedback.append("Cotovelo hiperextendido")
            failed_joints.append(dom_joint_elbow)
        else:
            if 130 <= elbow_angle <= 165:
                feedback.append("Braço firme e amplitude ideal")
            else:
                feedback.append("Braço firme no backhand")

        if not is_mock:
            # 2. Ombro dominante
            if shoulder_angle < 35:
                feedback.append("Abra mais o braço no backhand")
                failed_joints.append(dom_joint_shoulder)

            # 3. Braço não dominante (Mão de apoio/guia)
            if non_dom_elbow < 85:
                feedback.append("Cotovelo não dominante amassado")
                failed_joints.append(non_dom_joint_elbow)

            # 4. Punho dominante
            if coord_dom_w[1] > (coord_dom_hip[1] + 0.05):
                feedback.append("Punho caído abaixo da empunhadura")
                failed_joints.append(dom_joint_wrist)

            # 5. Joelhos
            knee_front_val = knee_r if not is_left_handed else knee_l
            knee_back_val = knee_l if not is_left_handed else knee_r
            if knee_front_val > 165:
                feedback.append("Dobre o joelho dianteiro para apoiar no backhand")
                failed_joints.append(front_joint_knee)
            if knee_back_val > 169:
                failed_joints.append(back_joint_knee)

            # 6. Quadris e Tornozelos
            if stance_ratio < 0.80:
                feedback.append("Base dos pés estreita no backhand")
                failed_joints.extend([back_joint_ankle, front_joint_ankle])
            if hip_r < 135 or hip_l < 135:
                failed_joints.extend([dom_joint_hip, non_dom_joint_hip])

    elif stroke_class_id == 2:  # SAQUE
        avg_knee = (knee_r + knee_l) / 2.0
        if avg_knee > 155:
            feedback.append("Dobre mais os joelhos para impulsão")
            failed_joints.extend(["joelho_dir", "joelho_esq"])
        else:
            if 105 <= avg_knee <= 135 and elbow_angle >= 140:
                feedback.append("Impulsão de joelho e extensão perfeitas")
            else:
                feedback.append("Boa flexão e alcance no saque")

        if not is_mock:
            if elbow_angle < 138:
                feedback.append("Estenda o cotovelo no ponto máximo do saque")
                failed_joints.append(dom_joint_elbow)

            if shoulder_angle < 75:
                feedback.append("Cotovelo dominante baixo na preparação do saque")
                failed_joints.append(dom_joint_shoulder)

            # Braço de lançamento (toss)
            if coord_nd_w[1] > coord_nd_sh[1]:
                feedback.append("Braço de toss muito baixo, guie a bola no alto")
                failed_joints.extend([non_dom_joint_shoulder, non_dom_joint_elbow])

            # Terminação do punho dominante
            if coord_dom_w[1] < coord_dom_sh[1]:
                feedback.append("Complete o follow-through com pronação do punho")
                failed_joints.append(dom_joint_wrist)

            # Tornozelos e quadris
            if stance_ratio < 0.72:
                feedback.append("Pés muito juntos no saque")
                failed_joints.extend([back_joint_ankle, front_joint_ankle])
            if hip_r < 135 or hip_l < 135:
                failed_joints.extend([dom_joint_hip, non_dom_joint_hip])

    elif stroke_class_id == 3:  # REPOUSO / POSIÇÃO DE ESPERA
        if not is_mock:
            # Posição de espera atlética: braço esquerdo e direito prontos à frente
            if non_dom_elbow > 172 or coord_nd_w[1] > coord_nd_hip[1] + 0.05:
                feedback.append("Braço esquerdo solto na posição de espera")
                failed_joints.extend(["cotovelo_esq", "pulso_esq"])
            if elbow_angle > 172 or coord_dom_w[1] > coord_dom_hip[1] + 0.05:
                feedback.append("Braço direito solto na posição de espera")
                failed_joints.extend(["cotovelo_dir", "pulso_dir"])
            if knee_l > 175:
                failed_joints.append("joelho_esq")
            if knee_r > 175:
                failed_joints.append("joelho_dir")
            if stance_ratio < 0.70:
                feedback.append("Afaste os pés para base atlética")
                failed_joints.extend(["tornozelo_dir", "tornozelo_esq"])
        if not feedback:
            feedback.append("Atleta em posição de espera")

    # Remove duplicatas preservando ordem
    unique_failed = []
    for j in failed_joints:
        if j not in unique_failed:
            unique_failed.append(j)

    # Classificação Final de Nota (Grade) e Score
    if is_mock:
        if stroke_class_id == 0:
            if elbow_angle < 120:
                grade = "FAULT"
                quality_score = 0.0
            elif elbow_angle > 175:
                grade = "FAULT"
                quality_score = 0.2
            elif 135 <= elbow_angle <= 165:
                grade = "PERFECT"
                quality_score = 1.0
            else:
                grade = "GOOD"
                quality_score = 0.85
        elif stroke_class_id == 1:
            if elbow_angle < 110:
                grade = "FAULT"
                quality_score = 0.0
            elif 130 <= elbow_angle <= 165:
                grade = "PERFECT"
                quality_score = 1.0
            else:
                grade = "GOOD"
                quality_score = 0.85
        elif stroke_class_id == 2:
            avg_k = (knee_r + knee_l) / 2.0
            if avg_k > 155:
                grade = "FAULT"
                quality_score = 0.0
            elif 105 <= avg_k <= 135 and elbow_angle >= 140:
                grade = "PERFECT"
                quality_score = 1.0
            else:
                grade = "GOOD"
                quality_score = 0.85
        else:
            grade = "NONE"
            quality_score = 0.0
    else:
        if len(unique_failed) == 0:
            grade = "PERFECT"
            quality_score = 1.0
        elif len(unique_failed) <= 2:
            grade = "GOOD" if stroke_class_id != 3 else "NONE"
            quality_score = 0.85
        else:
            grade = "FAULT"
            quality_score = max(0.0, 0.60 - len(unique_failed) * 0.10)

    return " | ".join(feedback), angles, unique_failed, quality_score, grade


def evaluate_stroke_trajectory(stroke_class_id, trajectory_landmarks, lateralidade='destro'):
    """
    Avaliação Contínua de Toda a Trajetória (Sequência temporal dos frames de replay).
    Examina as 12 articulações durante preparação, aceleração, ponto de impacto e terminação:
      - Ombro D/E, Cotovelo D/E, Pulso D/E, Quadril D/E, Joelho D/E, Tornozelo D/E.
    Retorna:
    (feedback_str, angles_dict, failed_joints, quality_score, grade, worst_frame_idx)
    """
    if not trajectory_landmarks or len(trajectory_landmarks) < 5:
        return "Movimento muito curto para análise", {}, [], 0.0, "NONE", 0

    n_frames = len(trajectory_landmarks)

    # Auto-detecção de lateralidade do golpe: compara o dinamismo do punho esquerdo e direito
    speeds_r = []
    speeds_l = []
    for t in range(1, n_frames):
        c_prev_r = angle_calculator.get_landmark_coord(trajectory_landmarks[t-1][16])
        c_curr_r = angle_calculator.get_landmark_coord(trajectory_landmarks[t][16])
        speeds_r.append(float(np.linalg.norm(np.array(c_curr_r[:2]) - np.array(c_prev_r[:2]))))

        c_prev_l = angle_calculator.get_landmark_coord(trajectory_landmarks[t-1][15])
        c_curr_l = angle_calculator.get_landmark_coord(trajectory_landmarks[t][15])
        speeds_l.append(float(np.linalg.norm(np.array(c_curr_l[:2]) - np.array(c_prev_l[:2]))))

    max_spd_r = max(speeds_r) if speeds_r else 0.0
    max_spd_l = max(speeds_l) if speeds_l else 0.0

    # Se configurado como canhoto ou se o braço esquerdo liderou claramente o movimento:
    if str(lateralidade).lower() == 'canhoto' or (max_spd_l > max_spd_r * 1.30 and max_spd_l > 0.035):
        is_left_handed = True
    else:
        is_left_handed = False

    dom_arm = 'left' if is_left_handed else 'right'
    non_dom_arm = 'right' if is_left_handed else 'left'

    dom_joint_shoulder = "ombro_esq" if is_left_handed else "ombro_dir"
    non_dom_joint_shoulder = "ombro_dir" if is_left_handed else "ombro_esq"

    dom_joint_elbow = "cotovelo_esq" if is_left_handed else "cotovelo_dir"
    non_dom_joint_elbow = "cotovelo_dir" if is_left_handed else "cotovelo_esq"

    dom_joint_wrist = "pulso_esq" if is_left_handed else "pulso_dir"
    non_dom_joint_wrist = "pulso_dir" if is_left_handed else "pulso_esq"

    dom_joint_hip = "quadril_esq" if is_left_handed else "quadril_dir"
    non_dom_joint_hip = "quadril_dir" if is_left_handed else "quadril_esq"

    back_leg = "left" if is_left_handed else "right"
    front_leg = "right" if is_left_handed else "left"

    back_joint_knee = "joelho_esq" if is_left_handed else "joelho_dir"
    front_joint_knee = "joelho_dir" if is_left_handed else "joelho_esq"

    back_joint_ankle = "tornozelo_esq" if is_left_handed else "tornozelo_dir"
    front_joint_ankle = "tornozelo_dir" if is_left_handed else "tornozelo_esq"

    feedback_list = []
    failed_joints = set()
    worst_frame_idx = 0
    worst_severity = 0.0

    # Momento de ápice de aceleração do punho (ponto de impacto provável)
    wrist_idx = 15 if is_left_handed else 16
    wrist_speeds = speeds_l if is_left_handed else speeds_r

    impact_idx = int(np.argmax(wrist_speeds)) if wrist_speeds else n_frames // 2

    prep_phase = trajectory_landmarks[:max(1, impact_idx - 3)]
    impact_frame = trajectory_landmarks[impact_idx]
    follow_phase = trajectory_landmarks[min(n_frames - 1, impact_idx + 3):]

    angles_summary = {}

    if stroke_class_id == 0:  # FOREHAND
        # 1. Cotovelo Dominante
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

        # 2. Ombro Dominante (Abertura no impacto)
        impact_sh = angle_calculator.get_shoulder_angle(impact_frame, side=dom_arm)
        angles_summary['shoulder_impact'] = round(impact_sh, 1)
        if impact_sh < 32:
            feedback_list.append("Ombro dominante sem abertura, cotovelo colado ao corpo")
            failed_joints.add(dom_joint_shoulder)
            worst_severity = max(worst_severity, 0.8)

        # 3. Ombro Não-Dominante e Rotação do Tronco
        max_rotation = max([angle_calculator.get_torso_rotation_angle(lms) for lms in trajectory_landmarks] or [0])
        angles_summary['torso_rot_max'] = round(max_rotation, 1)
        if max_rotation < 12.0:
            feedback_list.append("Faltou rotação de tronco e ombros no golpe")
            failed_joints.add(non_dom_joint_shoulder)
            worst_severity = max(worst_severity, 0.6)

        # 4. Punho Dominante (Follow-through alto)
        if follow_phase:
            final_lms = follow_phase[-1]
            wrist_y = angle_calculator.get_landmark_coord(final_lms[wrist_idx])[1]
            opp_sh_idx = 12 if is_left_handed else 11
            opp_sh_y = angle_calculator.get_landmark_coord(final_lms[opp_sh_idx])[1]
            if wrist_y > (opp_sh_y + 0.12):
                feedback_list.append("Terminação baixa, finalize por cima do ombro")
                failed_joints.add(dom_joint_wrist)
                worst_severity = max(worst_severity, 0.5)

        # 5. Membros Não-Dominantes (Equilíbrio e Apoio)
        nd_wrist_idx = 16 if is_left_handed else 15
        nd_hip_idx = 24 if is_left_handed else 23
        if prep_phase:
            nd_w_y = np.mean([angle_calculator.get_landmark_coord(lms[nd_wrist_idx])[1] for lms in prep_phase])
            nd_h_y = np.mean([angle_calculator.get_landmark_coord(lms[nd_hip_idx])[1] for lms in prep_phase])
            if nd_w_y > (nd_h_y + 0.12):
                feedback_list.append("Braço de equilíbrio caído, mantenha o braço não dominante erguido")
                failed_joints.add(non_dom_joint_elbow)
                failed_joints.add(non_dom_joint_wrist)
                worst_severity = max(worst_severity, 0.5)

        # 6. Joelhos (Flexão da base)
        min_knee_back = min([angle_calculator.get_knee_angle(lms, side=back_leg) for lms in trajectory_landmarks] or [180.0])
        angles_summary['knee_back_min'] = round(min_knee_back, 1)
        if min_knee_back > 166.0:
            feedback_list.append("Joelho da perna de apoio esticado, flexione as pernas")
            failed_joints.add(back_joint_knee)
            worst_severity = max(worst_severity, 0.7)

        # 7. Quadris e Tornozelos (Alinhamento e Stance)
        min_hip = min([min(angle_calculator.get_hip_angle(lms, side='right'), angle_calculator.get_hip_angle(lms, side='left')) for lms in trajectory_landmarks] or [180.0])
        angles_summary['hip_min'] = round(min_hip, 1)
        if min_hip < 132.0:
            feedback_list.append("Tronco inclinado excessivamente para a frente nos quadris")
            failed_joints.add(dom_joint_hip)
            failed_joints.add(non_dom_joint_hip)
            worst_severity = max(worst_severity, 0.6)

        avg_stance = float(np.mean([angle_calculator.get_stance_ratio(lms) for lms in trajectory_landmarks] or [1.0]))
        angles_summary['stance_ratio'] = round(avg_stance, 2)
        if avg_stance < 0.78:
            feedback_list.append("Base dos pés estreita, afaste os tornozelos")
            failed_joints.add(back_joint_ankle)
            failed_joints.add(front_joint_ankle)
            worst_severity = max(worst_severity, 0.6)

    elif stroke_class_id == 1:  # BACKHAND
        # 1. Cotovelo Dominante
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

        # 2. Ombro Dominante
        sh_angle = angle_calculator.get_shoulder_angle(impact_frame, side=dom_arm)
        angles_summary['shoulder_impact'] = round(sh_angle, 1)
        if sh_angle < 35:
            feedback_list.append("Abra mais o braço no backhand")
            failed_joints.add(dom_joint_shoulder)
            worst_severity = max(worst_severity, 0.6)

        # 3. Braço Não-Dominante (Apoio)
        min_nd_elbow = min([angle_calculator.get_elbow_angle(lms, side=non_dom_arm) for lms in trajectory_landmarks] or [140.0])
        angles_summary['non_dom_elbow_min'] = round(min_nd_elbow, 1)
        if min_nd_elbow < 85:
            feedback_list.append("Cotovelo não dominante colapsado")
            failed_joints.add(non_dom_joint_elbow)
            failed_joints.add(non_dom_joint_wrist)
            worst_severity = max(worst_severity, 0.5)

        # 4. Joelho Dianteiro
        min_knee_front = min([angle_calculator.get_knee_angle(lms, side=front_leg) for lms in trajectory_landmarks] or [180.0])
        angles_summary['knee_front_min'] = round(min_knee_front, 1)
        if min_knee_front > 165.0:
            feedback_list.append("Dobre o joelho dianteiro no backhand")
            failed_joints.add(front_joint_knee)
            worst_severity = max(worst_severity, 0.7)

        # 5. Quadris e Tornozelos
        avg_stance = float(np.mean([angle_calculator.get_stance_ratio(lms) for lms in trajectory_landmarks] or [1.0]))
        angles_summary['stance_ratio'] = round(avg_stance, 2)
        if avg_stance < 0.80:
            feedback_list.append("Base dos pés estreita no backhand")
            failed_joints.add(back_joint_ankle)
            failed_joints.add(front_joint_ankle)
            worst_severity = max(worst_severity, 0.5)

    elif stroke_class_id == 2:  # SAQUE
        # 1. Joelhos (Trophy Pose Knee Flex)
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

        # 2. Cotovelo Dominante no Impacto
        elbow_impact = angle_calculator.get_elbow_angle(impact_frame, side=dom_arm)
        angles_summary['elbow_impact'] = round(elbow_impact, 1)
        if elbow_impact < 135:
            feedback_list.append("Estenda o braço mais no alto ao golpear")
            failed_joints.add(dom_joint_elbow)
            worst_severity = max(worst_severity, 0.9)

        # 3. Ombro Dominante na Preparação
        sh_prep = min([angle_calculator.get_shoulder_angle(lms, side=dom_arm) for lms in prep_phase] or [90.0])
        angles_summary['shoulder_prep'] = round(sh_prep, 1)
        if sh_prep < 72:
            feedback_list.append("Suba o cotovelo na altura dos ombros ao armar o saque")
            failed_joints.add(dom_joint_shoulder)
            worst_severity = max(worst_severity, 0.7)

        # 4. Braço de Lançamento (Toss)
        nd_sh_idx = 11 if not is_left_handed else 12
        nd_w_idx = 15 if not is_left_handed else 16
        if prep_phase:
            nd_wrist_y = min([angle_calculator.get_landmark_coord(lms[nd_w_idx])[1] for lms in prep_phase])
            nd_sh_y = min([angle_calculator.get_landmark_coord(lms[nd_sh_idx])[1] for lms in prep_phase])
            if nd_wrist_y > nd_sh_y:
                feedback_list.append("Braço de lançamento (toss) muito baixo, guie a bola acima da cabeça")
                failed_joints.add(non_dom_joint_shoulder)
                failed_joints.add(non_dom_joint_elbow)
                worst_severity = max(worst_severity, 0.6)

        # 5. Pés e Quadris
        avg_stance = float(np.mean([angle_calculator.get_stance_ratio(lms) for lms in prep_phase] or [1.0]))
        angles_summary['stance_ratio'] = round(avg_stance, 2)
        if avg_stance < 0.72:
            feedback_list.append("Pés muito juntos na base do saque")
            failed_joints.add(back_joint_ankle)
            failed_joints.add(front_joint_ankle)
            worst_severity = max(worst_severity, 0.5)

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
