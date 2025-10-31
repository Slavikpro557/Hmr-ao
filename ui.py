#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gradio UI для HRM: чат / визуализатор / обучение (использует evaluate.py и pretrain.py из репо).
Положите этот файл в корень репо Hmr-ao (или используйте install.bat для копирования).
Адаптируйте пути/импорты под фактические сигнатуры в вашем репо.
"""
import os
import tempfile
import subprocess
import json
from pathlib import Path

import gradio as gr

DEFAULT_CHECKPOINT = "checkpoints/sudoku.ckpt"
DEFAULT_DEVICE = "cpu"

def load_checkpoint_info(path: str):
    p = Path(path)
    return p.exists(), str(p.resolve())

def parse_input_text(input_text: str, task_type: str):
    if not input_text:
        return {"error": "Пустой ввод"}
    if task_type == "sudoku":
        s = "".join(input_text.split())
        return {"task": "sudoku", "puzzle": s}
    elif task_type == "arc":
        try:
            obj = json.loads(input_text)
            return {"task": "arc", "json": obj}
        except Exception as e:
            return {"error": f"ARC JSON parse error: {e}"}
    elif task_type == "code":
        return {"task": "code", "code": input_text}
    else:
        return {"task": task_type, "raw": input_text}

def visualize_grid_as_html(grid):
    if not grid:
        return "<div>Пустой результат</div>"
    html = "<table style='border-collapse: collapse;'>"
    for row in grid:
        html += "<tr>"
        for cell in row:
            html += f"<td style='border:1px solid #444;padding:6px;text-align:center'>{cell if cell is not None else ''}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def call_evaluate_subprocess(input_payload: dict, checkpoint: str, task_type: str, timeout=30):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    try:
        json.dump(input_payload, tmp)
        tmp.flush()
        tmp.close()
        # ВАЖНО: адаптируйте CLI evaluate.py если нужно
        cmd = [
            "python", "evaluate.py",
            "--checkpoint", checkpoint,
            "--input-file", tmp.name,
            "--task", task_type
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return {"error": f"evaluate exit {proc.returncode} stderr: {proc.stderr}"}
        try:
            out = json.loads(proc.stdout)
            return {"result": out}
        except Exception:
            return {"result_text": proc.stdout}
    except subprocess.TimeoutExpired:
        return {"error": "evaluate timed out"}
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

def chat_with_hrm(input_text, task_type, checkpoint, device):
    info = parse_input_text(input_text, task_type)
    if "error" in info:
        return info["error"]

    ck_exists, ck_path = load_checkpoint_info(checkpoint)
    if not ck_exists:
        return f"Чекпоинт не найден: {checkpoint}"

    resp = call_evaluate_subprocess(info, checkpoint, task_type)
    if "error" in resp:
        return resp["error"]
    if "result" in resp:
        r = resp["result"]
        if isinstance(r, list):
            return visualize_grid_as_html(r)
        return json.dumps(r, ensure_ascii=False, indent=2)
    return resp.get("result_text", "Нет результата")

def train_model_entry(dataset_file, epochs, lr, checkpoint_out, extra_cmd):
    if dataset_file is None:
        return "Ошибка: датасет не загружен."
    if hasattr(dataset_file, "name"):
        data_path = dataset_file.name
    else:
        data_path = str(dataset_file)

    cmd = [
        "OMP_NUM_THREADS=8",
        "torchrun", "--nproc-per-node", "1",
        "pretrain.py",
        f"--data_path={data_path}",
        f"--epochs={int(epochs)}",
        f"--lr={float(lr)}",
        f"--checkpoint_out={checkpoint_out}"
    ]
    if extra_cmd:
        cmd.append(extra_cmd)

    cmd_str = " ".join(cmd)
    try:
        proc = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=60*60*6)
        if proc.returncode != 0:
            return f"pretrain exit {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        return f"Обучение завершено. Чекпоинт (ожидается): {checkpoint_out}\n\nПоследние 800 символов stdout:\n{proc.stdout[-800:]}">
    except subprocess.TimeoutExpired:
        return "Обучение превысило лимит времени."

def build_ui():
    with gr.Blocks(title="HRM UI — Chat, Training, Visualizer") as demo:
        gr.Markdown("# HRM UI — чат, обучение и визуализация")
        with gr.Tab("Чат с моделью"):
            with gr.Row():
                inp = gr.Textbox(lines=6, label="Ввод задачи")
                task = gr.Dropdown(choices=["sudoku", "arc", "code"], value="sudoku", label="Тип задачи")
            with gr.Row():
                ckpt = gr.Textbox(value=DEFAULT_CHECKPOINT, label="Путь до чекпоинта")
                device = gr.Dropdown(choices=["cpu", "cuda"], value=DEFAULT_DEVICE, label="Device")
                run_btn = gr.Button("Решить")
            output_html = gr.HTML(label="Результат")
            run_btn.click(fn=chat_with_hrm, inputs=[inp, task, ckpt, device], outputs=output_html)

        with gr.Tab("Визуализация"):
            file_upload = gr.File(label="Загрузите JSON (пример)")
            show_btn = gr.Button("Показать содержимое")
            json_out = gr.JSON()
            def show_file(f):
                if f is None:
                    return {"error": "Файл не загружен"}
                try:
                    with open(f.name, "r", encoding="utf8") as fh:
                        data = json.load(fh)
                    return data
                except Exception as e:
                    return {"error": str(e)}
            show_btn.click(show_file, inputs=file_upload, outputs=json_out)

        with gr.Tab("Обучение"):
            ds_upload = gr.File(label="Датасет (json)")
            epochs = gr.Slider(minimum=1, maximum=20000, step=1, value=5000, label="Эпохи")
            lr = gr.Number(value=1e-4, label="Learning rate")
            ckout = gr.Textbox(value="checkpoints/custom.ckpt", label="Куда сохранить чекпоинт")
            extra = gr.Textbox(label="Доп. аргументы для pretrain.py (опционально)")
            train_btn = gr.Button("Запустить обучение")
            train_log = gr.Textbox(label="Лог запуска", lines=10)
            train_btn.click(fn=train_model_entry, inputs=[ds_upload, epochs, lr, ckout, extra], outputs=train_log)

    return demo

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
