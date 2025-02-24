 

import datetime
from enum import Enum
import os
import shutil
from turtle import pd
from typing import List
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel



class FolderEnum(str, Enum):
    GENERAL_INFORMATION = "results1"
    MIXED_INFORMATION = "results2"
    RELEVANCE = "results3"
    INFERENCE = "results4"

class CreateTaskRequest(BaseModel):
    folders: List[str]
    questions: List[str]
    range_value: int
    limit: int = 20000 



router = APIRouter()
dir_path = r"/path/"
words_list_folder = os.path.join(dir_path, "words_list")
results_folder = os.path.join(dir_path, "think_tank_results")
os.makedirs(words_list_folder, exist_ok=True)


# try:
#     shutil.rmtree(results_folder)
# except Exception as e:
#     print(e)


def save_file(folder_name: str, file: UploadFile):
    folder_path = os.path.join(words_list_folder, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, file.filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
 
def process_task():
    print("process_task")


@router.post("/upload_docs/", response_class=JSONResponse)
def upload_docs(
    folder_name: str = Form(...),
    files: List[UploadFile] = File(...),
):
    folder_path = os.path.join(words_list_folder, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    for file in files:
        save_file(folder_name, file)
    return JSONResponse({"status": "ok"}) 



@router.get("/list_docs/", response_class=JSONResponse)
def list_docs():
    folders = os.listdir(words_list_folder) 
    folders_dict = {}
    
    for folder in folders:
        folder_path = os.path.join(words_list_folder, folder) 
        if os.path.isdir(folder_path):  
            files = os.l



@router.post("/create_task/", response_class=JSONResponse) 
def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
):
    folders = request.folders
    questions = request.questions
    range_value = request.range_value
    limit = request.limit

    folders_str = ""
    for folder in folders:
        folders_str += "_" + folder
    now = datetime.datetime.now().strftime("%Y_%m_%d_%H%M") + folders_str
    result_subfolder = os.path.join(results_folder, now)
    os.makedirs(result_subfolder, exist_ok=True)
    
    background_tasks.add_task(process_task, result_subfolder, folders, questions, range_value, limit)

    return JSONResponse(status_code=201, content={"message": "Operation started successfully", "result_id": now})


@router.get("/get_task_results_status/{restult_id}", response_class=JSONResponse)
def get_results(restult_id: str):
    single_results_folder = os.path.join(results_folder, restult_id)
    if not os.path.exists(single_results_folder):
        return JSONResponse(status_code=404, content={"message": "No results found with this name"})

    calculation_done = os.path.exists(os.path.join(single_results_folder, "calculation_done.txt"))
    status_code = 200 if calculation_done else 425
    return JSONResponse(status_code=status_code, content={
        "message": f"{'Results are available' if status_code == 200 else 'The system is still processing, please wait'}"
    })


@router.get("/list_csv_files/{results_id}/{folder_name}", response_class=JSONResponse)
def list_csv_files(results_id: str , folder_name: FolderEnum):
    
    folder_path = os.path.join(results_folder, results_id, folder_name.value)
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".csv") or f.lower().endswith(".txt")]

    if not csv_files:
        return JSONResponse(status_code=204, content={"message": "No CSV files are available in this folder"})

    return JSONResponse(content={"folder": folder_name.value, "csv_files": csv_files})


@router.get("/get_file_content/{results_id}/{folder_name}/{file_name}", response_class=JSONResponse)
def get_file_content(results_id: str, folder_name: FolderEnum, file_name: str):
    file_path = os.path.join(results_folder, results_id, folder_name.value, file_name)

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"message": "File not found!"})

    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(file_path) 
            df.replace([float("inf"), float("-inf")], None, inplace=True)
            df.fillna(value="", inplace=True)
            data = df.to_dict(orient="records")
        elif file_name.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = f.read()
        else:
            return JSONResponse(status_code=400, content={"message": "File format not supported"})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error reading the file", "detail": str(e)})
        
    return JSONResponse(content={"file_name": file_name, "data": data})


@router.delete("/delete_docs/{folder_name}", response_class=JSONResponse)
def delete_folder(folder_name: str):
    folder_path = os.path.join(words_list_folder, folder_name)

    if not os.path.exists(folder_path):
        return JSONResponse(status_code=404, content={"message": "The requested folder was not found"})

    try:
        shutil.rmtree(folder_path)
    except PermissionError:
        return JSONResponse(status_code=403, content={"message": "Folder deletion encountered an access error"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Internal error while deleting the folder", "detail": str(e)})

    return JSONResponse(status_code=204, content={"message": "Folder successfully deleted."})
