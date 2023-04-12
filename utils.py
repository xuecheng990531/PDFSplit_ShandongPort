import paddleocr
from paddleocr import  PaddleOCR
import os
import fitz
import re
#2.5.0
import PyPDF2
import aiofiles
import shutil
import io
import zipfile
from fastapi.responses import StreamingResponse

ocr = PaddleOCR(use_angle_cls=False,lang="ch",workers=1,use_gpu=True,det_limit_side_len=1216,use_multiprocess=False)

async def save_img(File, filename):
    async with aiofiles.open(os.path.join('upload_files', filename),'wb') as out_file:
        content = await File.read()
        await out_file.write(content)

def del_upload_file():
    dir1 = 'upload_files'
    dir2 = 'save_files'
    dir3 = 'split_pdfs'
    dir4 = 'new_filenames'
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
    with open(os.path.join('upload_files',str(filename)), 'rb') as input_file:
        pdf_reader = PyPDF2.PdfFileReader(input_file)

        # 创建一个用于保存特定字段之前所有页面的输出 PDF 对象
        output_pdf = PyPDF2.PdfFileWriter()

        # 遍历每一页，检查是否包含特定字段
        for page_num in range(pdf_reader.numPages):
            page_obj = pdf_reader.getPage(page_num)
            text = page_obj.extract_text()
            if 'LADING' in text or 'WAYBILL' in text:
                # 如果发现特定字段，则将之前的所有页面合并为一个 PDF 文件
                with open('split_pdfs/output_{}.pdf'.format(page_num), 'wb') as output_file:
                    output_pdf.write(output_file)
                # 创建一个新的 PDF 输出对象以便下一次使用
                output_pdf = PyPDF2.PdfFileWriter()
            # 否则，将当前页面添加到输出 PDF 对象中
            output_pdf.addPage(page_obj)

        # 将最后一次创建的 PDF 输出对象写入文件，以包括所剩下的页面
        with open('split_pdfs/output.pdf', 'wb') as output_file:
            output_pdf.write(output_file)

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
        pix.save('save_files/' + img_name +
                 '_%s.png' % page.number)  # store image as a PNG
        img_list.append('save_files/' + img_name + '_%s.png' % page.number)
    return page_count, img_list

def search_rename(pos,value,name):
    for i in range(len(value)):
        # if 'Export' in value[i] and len(value[i].split('ort')[-1])!=0:
        #     shr_pos = pos[i]
        #     height = pos[i][3][1] - pos[i][0][1]
        #     width = pos[i][1][0] - pos[i][0][0]
        #     for i in range(len(pos)):
        #         if shr_pos[0][0]-width/2 < pos[i][0][0] < shr_pos[1][0] + width*2 and shr_pos[1][1] -height*4 < pos[i][2][1] < shr_pos[1][1]+height/2 and value[i].isdigit():
        #             print(value[i])
        #             if os.path.exists('split_pdfs/'+str(name)):
        #                 shutil.copy('split_pdfs/'+str(name),'new_filenames/')
        #                 os.rename('new_filenames/'+str(name),'new_filenames/'+str(value[i])+'.pdf')

        if value[i].isdigit() and len(value[i])==12:
            result = re.findall(r'\d+', value[i])
            if len(result)!=0:
                if os.path.exists('split_pdfs/'+str(name)):
                    shutil.copy('split_pdfs/'+str(name),'new_filenames/')
                    os.rename('new_filenames/'+str(name),'new_filenames/'+str(result[0])+'.pdf')
                    break
                break


def rename():
    dir='split_pdfs'
    number=len(os.listdir(dir))
    for i in range(number):
        name=os.listdir(dir)[i]
        page_count, img_list=pdf_img(pdfPath=os.path.join(dir,name),img_name=name)
        pos,value=detect_pdf(img_list=img_list,page_no=page_count)
        search_rename(pos,value,name)