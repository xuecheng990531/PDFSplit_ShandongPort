import paddleocr
from paddleocr import  PaddleOCR
from fastapi import FastAPI, File, UploadFile
import requests
from typing import List
import os
import fitz
import re
#2.5.0
import PyPDF2
import aiofiles
import shutil
import io
import zipfile
import multiprocessing as mp
from fastapi.responses import StreamingResponse

ocr = PaddleOCR(use_angle_cls=False,lang="ch",workers=12,use_gpu=True,det_limit_side_len=1216,use_multiprocess=True)

async def save_file(File, filename):
    async with aiofiles.open(os.path.join('UploadFile', filename),'wb') as out_file:
        content = await File.read()
        await out_file.write(content)

def upload_folder() -> List[dict]:
    url = "http://api.sdland-sea.com/api-lh-oss/lh-oss/uploadFile"
    folder_path = "NewPDFs"  # 替换为要上传的文件夹路径
    metadata_list = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                files = {"file": (filename, f)}
                response = requests.post(url, files=files)
                if response.status_code == 200:
                    data = response.json()
                    metadata_list.append({'blno': filename, 'downloadPath': data['url'],"msg": "上传至服务器"})
                else:
                    return {'error': f'上传失败：{filename}'}
                
        elif os.path.isdir(file_path):
            return {'error': '不支持上传文件夹内的文件夹'}
    # OSS服务器返回的信息，包含blno和downloadpath
    info_return= {"downPathList":metadata_list}
    return info_return



def HuiZhi(data: dict):
    url='https://shipagentgateway.sdland-sea.com/online/api/services/app/EMC/BLDownloadSave'
    headers = {"Content-type": "application/json"}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return {
            "success":response.json()["success"],
            "msg":response.json()["msg"]
            }
    else:
        return {"error": "Failed to upload JSON data"}



def del_upload_file():
    dir1 = 'UploadFile'
    dir2 = 'SavePics'
    dir3 = 'SplitedPDF'
    dir4 = 'NewPDFs'
    for root, dirs, files in os.walk(dir1):
        for name in files:
            if name.endswith(".pdf"):
                os.remove(os.path.join(root, name))
    for root, dirs, files in os.walk(dir2):
        for name in files:
            if name.endswith(".png"):
                os.remove(os.path.join(root, name))
    for root, dirs, files in os.walk(dir3):
        for name in files:
            if name.endswith(".pdf"):
                os.remove(os.path.join(root, name))
    for root, dirs, files in os.walk(dir4):
        for name in files:
            if name.endswith(".pdf"):
                os.remove(os.path.join(root, name))

def split_chars(filename):
    with open(os.path.join('UploadFile',str(filename)), 'rb') as input_file:
        pdf_reader = PyPDF2.PdfFileReader(input_file)

        # 创建一个用于保存特定字段之前所有页面的输出 PDF 对象
        output_pdf = PyPDF2.PdfFileWriter()

        # 遍历每一页，检查是否包含特定字段
        for page_num in range(pdf_reader.numPages):
            page_obj = pdf_reader.getPage(page_num)
            text = page_obj.extract_text()
            if 'LADING' in text or 'WAYBILL' in text:
                # 如果发现特定字段，则将之前的所有页面合并为一个 PDF 文件
                with open('SplitedPDF/output_{}.pdf'.format(page_num), 'wb') as output_file:
                    output_pdf.write(output_file)
                # 创建一个新的 PDF 输出对象以便下一次使用
                output_pdf = PyPDF2.PdfFileWriter()
            # 否则，将当前页面添加到输出 PDF 对象中
            output_pdf.addPage(page_obj)

        # 将最后一次创建的 PDF 输出对象写入文件，以包括所剩下的页面
        with open('SplitedPDF/output.pdf', 'wb') as output_file:
            output_pdf.write(output_file)
        
        folder_path='SplitedPDF'
        for file_name in os.listdir(folder_path):
            print('开始处理{}\n'.format(file_name))
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                page_count, img_list=pdf_img(pdfPath=file_path,img_name=file_name)
                pos,value=detect_pdf(img_list=img_list,page_no=page_count)
                search_rename(pos,value,file_name)
        

        


def detect_img(img_path):
    result = ocr.ocr(img_path, cls=False)
    pos = []
    value = []
    version = paddleocr.VERSION
    if '2.6' in version:
        result = result[0]
        for i in range(len(result)):
            pos.append(result[i][0])
            value.append(result[i][1][0])
    else:
        for i in range(len(result)):
            pos.append(result[i][0])
            value.append(result[i][1][0])
    return pos, value


def detect_pdf(img_list, page_no):
    if page_no == 1:
        pos, value = detect_img(img_list[0])
        return pos, value
    else:
        value_all = []
        pos_all = []
        for index in range(page_no):
            pos, value = detect_img(img_list[index])
            value_all.extend(value)
            pos_all.extend(pos)
        return pos_all, value_all
    

def pdf_img(pdfPath, img_name):
    img_list = []
    doc = fitz.open(pdfPath)
    page_count = doc.page_count
    for page in doc:
        pix = page.get_pixmap(dpi=300)  # render page to an image
        pix.save('SavePics/' + img_name +
                 '_%s.png' % page.number)  # store image as a PNG
        img_list.append('SavePics/' + img_name + '_%s.png' % page.number)
    return page_count, img_list
    
            

def search_rename(pos,value,name):
    for i in range(len(value)):
        if value[i].isdigit() and len(value[i])==12:
            result = re.findall(r'\d+', value[i])
            if len(result)!=0:
                if os.path.exists('SplitedPDF/'+str(name)):
                    shutil.copy('SplitedPDF/'+str(name),'NewPDFs/')
                    os.rename('NewPDFs/'+str(name),'NewPDFs/'+str(result[0])+'.pdf')
                    break
                break
        # else:
        #     if os.path.exists('SplitedPDF/'+str(name)):
        #         shutil.copy('SplitedPDF/'+str(name),'NewPDFs/')
        #         os.rename('NewPDFs/'+str(name),'NewPDFs/Wrong.pdf')


def rename():
    dir='SplitedPDF'
    number=len(os.listdir(dir))
    for i in range(number):
        print('开始处理第{}张PDF文件\n'.format(i+1))
        print('剩下{}张等待处理\n'.format(number-(i+1)))

        name=os.listdir(dir)[i]
        page_count, img_list=pdf_img(pdfPath=os.path.join(dir,name),img_name=name)
        pos,value=detect_pdf(img_list=img_list,page_no=page_count)
        search_rename(pos,value,name)
