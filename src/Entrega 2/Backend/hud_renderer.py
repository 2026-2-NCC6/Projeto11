import cv2
import numpy as np
import time

def draw_rounded_rect(img, pt1, pt2, color, thickness=-1, radius=10):
    """Desenha um retângulo com cantos arredondados no OpenCV."""
    x1, y1 = pt1
    x2, y2 = pt2
    w = x2 - x1
    h = y2 - y1
    radius = min(radius, w // 2, h // 2)

    if thickness == -1:
        # Preenchimento
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
        cv2.circle(img, (x1 + radius, y1 + radius), radius, color, -1)
        cv2.circle(img, (x2 - radius, y1 + radius), radius, color, -1)
        cv2.circle(img, (x1 + radius, y2 - radius), radius, color, -1)
        cv2.circle(img, (x2 - radius, y2 - radius), radius, color, -1)
    else:
        # Contorno
        cv2.line(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
        cv2.line(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
        cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness)
        cv2.line(img, (x2, y1 + radius), (x2, y2 - radius), color, thickness)
        cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)
        cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)

class TennisHUD:
    """
    Renderizador visual de alta performance para HUD Arcade do TennisSync.
    Opera diretamente sobre numpy arrays (BGR frames) do OpenCV com alpha blending.
    """
    def __init__(self):
        pass

    def render(self, frame, game_telemetry, fps=30):
        """
        Desenha a interface completa de jogo no frame.
        Retorna o frame anotado.
        """
        if frame is None:
            return None

        h, w, _ = frame.shape
        overlay = frame.copy()

        # 1. Barra Superior Translúcida (HUD Header)
        header_height = 80
        cv2.rectangle(overlay, (0, 0), (w, header_height), (15, 23, 42), -1) # Cor slate-900
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Divisor de linha brilhante
        cv2.line(frame, (0, header_height), (w, header_height), (59, 130, 246), 2)

        # 2. Informações do Lado Esquerdo: Marca, Nível e XP
        level = game_telemetry.get("level", 1)
        rank_title = game_telemetry.get("rank_title", "Iniciante")
        xp_progress = game_telemetry.get("xp_progress", 0.0)

        cv2.putText(frame, "TENNISSYNC RALLY", (18, 30), cv2.FONT_HERSHEY_DUPLEX, 0.65, (56, 189, 248), 2)
        cv2.putText(frame, f"NV {level} - {rank_title}", (18, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (203, 213, 225), 1)

        # Mini barra de XP
        bar_x = 18
        bar_y = 65
        bar_w = 140
        bar_h = 6
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (51, 65, 85), -1)
        fill_w = int((xp_progress / 100.0) * bar_w)
        if fill_w > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (34, 197, 94), -1)

        # 3. Centro: Contador de Rally e Combo
        rally_count = game_telemetry.get("rally_count", 0)
        combo_multiplier = game_telemetry.get("combo_multiplier", 1.0)
        combo_streak = game_telemetry.get("combo_streak", 0)

        rally_color = (0, 255, 127) if rally_count > 0 else (148, 163, 184)
        rally_text = f"RALLY: {rally_count}"
        cv2.putText(frame, rally_text, (w // 2 - 80, 42), cv2.FONT_HERSHEY_DUPLEX, 1.1, rally_color, 2)

        combo_color = (0, 215, 255) if combo_multiplier > 1.0 else (148, 163, 184)
        combo_text = f"COMBO x{combo_multiplier:.1f} ({combo_streak}x)"
        cv2.putText(frame, combo_text, (w // 2 - 70, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.55, combo_color, 2)

        # 4. Lado Direito: Vidas e Placar
        score = game_telemetry.get("score", 0)
        lives = game_telemetry.get("lives", 3)
        max_lives = game_telemetry.get("max_lives", 3)

        score_text = f"PTS: {score:05d}"
        cv2.putText(frame, score_text, (w - 200, 34), cv2.FONT_HERSHEY_DUPLEX, 0.75, (250, 204, 21), 2)

        # Desenhar corações / indicadores de vida
        heart_start_x = w - 190
        for i in range(max_lives):
            hx = heart_start_x + (i * 30)
            hy = 58
            if i < lives:
                # Vida ativa (Círculo preenchido vermelho brilhante)
                cv2.circle(frame, (hx, hy), 9, (68, 68, 239), -1)
                cv2.circle(frame, (hx, hy), 9, (255, 255, 255), 1)
            else:
                # Vida perdida (Círculo cinza escuro)
                cv2.circle(frame, (hx, hy), 9, (50, 50, 60), -1)
                cv2.circle(frame, (hx, hy), 9, (100, 100, 110), 1)

        # 5. Badge de Golpe / Toast Temporário
        last_grade = game_telemetry.get("last_grade", "NONE")
        last_points = game_telemetry.get("last_points", 0)
        last_feedback = game_telemetry.get("last_feedback", "")
        last_stroke_name = game_telemetry.get("last_stroke_name", "")

        if last_grade != "NONE" and last_stroke_name not in ["Repouso", ""]:
            badge_y = 100
            badge_h = 45
            badge_w = min(480, w - 40)
            badge_x = (w - badge_w) // 2

            if last_grade == "PERFECT":
                bg_color = (22, 101, 52)      # Verde escuro
                border_color = (34, 197, 94)   # Verde brilhante
                grade_label = f"PERFECT! +{last_points}"
            elif last_grade == "GOOD":
                bg_color = (20, 83, 154)      # Azul escuro
                border_color = (56, 189, 248)  # Ciano brilhante
                grade_label = f"GOOD SHOT! +{last_points}"
            else:
                bg_color = (127, 29, 29)      # Vermelho escuro
                border_color = (239, 68, 68)   # Vermelho brilhante
                grade_label = "FAULT! -1 VIDA"

            toast_overlay = frame.copy()
            draw_rounded_rect(toast_overlay, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), bg_color, -1, 8)
            cv2.addWeighted(toast_overlay, 0.85, frame, 0.15, 0, frame)
            draw_rounded_rect(frame, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), border_color, 2, 8)

            cv2.putText(frame, grade_label, (badge_x + 16, badge_y + 28), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, last_feedback[:45], (badge_x + 180, badge_y + 27), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (226, 232, 240), 1)

        # 6. Aviso de Conquista Desbloqueada (se houver)
        achievement = game_telemetry.get("new_achievement")
        if achievement:
            ach_w = 400
            ach_h = 42
            ach_x = (w - ach_w) // 2
            ach_y = h - 60
            ach_overlay = frame.copy()
            draw_rounded_rect(ach_overlay, (ach_x, ach_y), (ach_x + ach_w, ach_y + ach_h), (30, 27, 75), -1, 8)
            cv2.addWeighted(ach_overlay, 0.9, frame, 0.1, 0, frame)
            draw_rounded_rect(frame, (ach_x, ach_y), (ach_x + ach_w, ach_y + ach_h), (234, 179, 8), 2, 8)

            ach_text = f"CONQUISTA: {achievement['title']}!"
            cv2.putText(frame, ach_text, (ach_x + 18, ach_y + 26), cv2.FONT_HERSHEY_DUPLEX, 0.55, (250, 204, 21), 2)

        # 7. Tela de Game Over
        if game_telemetry.get("is_game_over", False):
            go_overlay = frame.copy()
            cv2.rectangle(go_overlay, (0, 0), (w, h), (15, 23, 42), -1)
            cv2.addWeighted(go_overlay, 0.88, frame, 0.12, 0, frame)

            box_w = min(520, w - 40)
            box_h = 320
            bx1 = (w - box_w) // 2
            by1 = (h - box_h) // 2
            bx2 = bx1 + box_w
            by2 = by1 + box_h

            draw_rounded_rect(frame, (bx1, by1), (bx2, by2), (30, 41, 59), -1, 16)
            draw_rounded_rect(frame, (bx1, by1), (bx2, by2), (239, 68, 68), 3, 16)

            cv2.putText(frame, "GAME OVER", (bx1 + box_w // 2 - 130, by1 + 60), cv2.FONT_HERSHEY_DUPLEX, 1.4, (239, 68, 68), 3)

            best_rally = game_telemetry.get("best_rally", 0)
            total_strokes = game_telemetry.get("total_strokes", 0)
            accuracy = game_telemetry.get("accuracy", 0.0)

            stats_lines = [
                f"Pontuacao Final: {score} pts",
                f"Melhor Rally: {best_rally} rebatidas",
                f"Golpes Realizados: {total_strokes}",
                f"Precisao Biomecanica: {accuracy}%"
            ]

            line_y = by1 + 115
            for line in stats_lines:
                cv2.putText(frame, line, (bx1 + 45, line_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (241, 245, 249), 2)
                line_y += 35

            # Instrução para reiniciar
            cv2.putText(frame, "Pressione 'R' para Jogar Novamente", (bx1 + 55, by1 + 280),
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, (56, 189, 248), 2)

        # FPS no canto inferior esquerdo
        cv2.putText(frame, f"FPS: {int(fps)}", (16, h - 16), cv2.FONT_HERSHEY_PLAIN, 1.3, (148, 163, 184), 1)

        return frame
