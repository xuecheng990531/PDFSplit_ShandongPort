import os
import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi import FastAPI, UploadFile, File, applications
from typing import List
from starlette.responses import FileResponse
from utils import *
import shutil
import zipfile

def swagger_monkey_patch(*args, **kwargs):
    return get_swagger_ui_html(
        *args,
        **kwargs,
        swagger_js_url=
        'https://cdn.bootcdn.net/ajax/libs/swagger-ui/4.10.3/swagger-ui-bundle.js',
        swagger_css_url=
        'https://cdn.bootcdn.net/ajax/libs/swagger-ui/4.10.3/swagger-ui.css')


applications.get_swagger_ui_html = swagger_monkey_patch

app = FastAPI(title='PDF拆分')



@app.post('/pdf')
async def ocr(File: UploadFile = File(...)):
    folder_path = "new_filenames"
    await save_img(File, File.filename)
    split_chars(filename=File.filename)
    rename()

    zip_file = io.BytesIO()
    with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.relpath(file_path, folder_path))

    # 将 ZIP 文件作为响应返回给客户端
    zip_file.seek(0)


    del_upload_file()
    
    return StreamingResponse(zip_file, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=Split_PDF.zip"})
    

if __name__ == '__main__':
    uvicorn.run(app='app:app', host='0.0.0.0', port=8009, reload=True)