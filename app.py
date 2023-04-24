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



@app.post('/pdf',tags=["执行完成后需要手动点击Download File下载拆分后的PDF文件，900页的pdf文件预计时间为20分钟左右！！"])
async def ocr(File: UploadFile = File(...,description='上传需要拆分的PDF')):
    await save_file(File, File.filename)
    split_chars(filename=File.filename)
    # 将所有字符图像文件上传到API端点
    info_return = upload_folder()
    del_upload_file()
    return HuiZhi(data=info_return)

    

if __name__ == '__main__':
    uvicorn.run(app='app:app', host='0.0.0.0', port=8009, reload=True)