import uvicorn
from fastapi import FastAPI, UploadFile, File,BackgroundTasks
from utils2025 import *


app = FastAPI(title='PDF拆分',openapi_version="3.0.0")

@app.post('/pdf')
async def ocr(background_tasks: BackgroundTasks,File: UploadFile = File(...,description='上传需要拆分的PDF')):
    await save_file(File, File.filename)
    background_tasks.add_task(handle_file, File.filename)
    return {"success":True,"Message":"上传成功,后台开始拆分"}

if __name__ == '__main__':
    uvicorn.run(app='app:app', host='0.0.0.0', port=8009, reload=True,workers=2)
