import os
import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi import FastAPI, UploadFile, File, applications,BackgroundTasks,Depends
from utils import *

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

async def add_delay():
    time.sleep(1)

@app.post('/pdf',tags=["执行完成后需要手动点击Download File下载拆分后的PDF文件，900页的pdf文件预计时间为20分钟左右！！"])
async def ocr(background_tasks: BackgroundTasks,File: UploadFile = File(...,description='上传需要拆分的PDF'),delay: bool = Depends(add_delay)):

    
    await save_file(File, File.filename)
    background_tasks.add_task(split_chars, File.filename)
    background_tasks.add_task(rename)
    return {"success":True,"Message":"上传成功,后台开始拆分"}

if __name__ == '__main__':
    uvicorn.run(app='app:app', host='0.0.0.0', port=8009, reload=True,workers=2)
