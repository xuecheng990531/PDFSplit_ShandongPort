from paddleocr import  PaddleOCR
import requests
import os
import fitz
import  time
#2.5.0
import PyPDF2
import aiofiles
import logging
from logutils import *

logging.getLogger('ppocr').setLevel(logging.ERROR)
ocr = PaddleOCR(use_angle_cls=False,lang="ch",workers=12,use_gpu=True,det_limit_side_len=1216,use_multiprocess=True)

async def save_file(File, filename):
    async with aiofiles.open(os.path.join('UploadFile', filename),'wb') as out_file:
        content = await File.read()
        await out_file.write(content)
        print('文件上传成功')


def delete_nonnumeric_pdfs(folder_path):
    for filename in os.listdir(folder_path):  # 遍历文件夹中的所有文件和子文件夹
        file_path = os.path.join(folder_path, filename)  # 获取文件路径
        if os.path.isfile(file_path):  # 如果是文件
            base_filename, ext = os.path.splitext(filename)  # 拆分文件名和扩展名
            if ext.lower() == '.pdf' and not base_filename.isdigit():  # 如果是 PDF 文件，并且文件名不是数字开头
                os.remove(file_path)  # 删除文件


def del_upload_file():
    for root, dirs, files in os.walk('UploadFile'):
        for name in files:
            if name.endswith(".pdf"):
                os.remove(os.path.join(root, name))

def split_chars(filename):
    
    dir_path='UploadFile/'
    for filename in os.listdir(dir_path):
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
                    with open('SplitedPDF/{}_{}.pdf'.format(filename,page_num), 'wb') as output_file:
                        output_pdf.write(output_file)
                    # 创建一个新的 PDF 输出对象以便下一次使用
                    output_pdf = PyPDF2.PdfFileWriter()
                # 否则，将当前页面添加到输出 PDF 对象中
                output_pdf.addPage(page_obj)

            # 将最后一次创建的 PDF 输出对象写入文件，以包括所剩下的页面
            with open('SplitedPDF/{}.pdf'.format(filename), 'wb') as output_file:
                output_pdf.write(output_file)
                
        
        print('文件{}拆分完成，开始重命名\n'.format(str(filename)))
        os.remove(os.path.join('UploadFile',str(filename)))
                
def rename():
    folder_path='SplitedPDF'
    s=time.time()
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            page_count, img_list=pdf_img(pdfPath=file_path,img_name=file_name)
            pos,value=detect_pdf(img_list=img_list,page_no=page_count)
            search_rename(pos,value,file_name)
        print('待处理文件还有{}个'.format(len(os.listdir(folder_path))))
    e=time.time()
    print('处理完成！总用时{}秒'.format(e-s))
            
    
    # 删除没有提单号的pdf
    delete_nonnumeric_pdfs(folder_path)
            



def detect_img(img_path):
    result = ocr.ocr(img_path, cls=False)
    pos = []
    value = []

    result = result[0]
    for i in range(len(result)):
        pos.append(result[i][0])
        value.append(result[i][1][0])

    return pos, value


def detect_pdf(img_list, page_no):
    value_all = []
    pos_all = []
    for index in range(page_no):
        pos, value = detect_img(img_list[index])
        value_all.extend(value)
        pos_all.extend(pos)
        if os.path.exists(img_list[index]):
            os.remove(img_list[index])
    return pos_all, value_all
    

def pdf_img(pdfPath, img_name):
    img_list = []
    doc = fitz.open(pdfPath)
    page_count = doc.page_count
    for page in doc:
        pix = page.get_pixmap(dpi=300)  # render page to an image
        pix.save('SavePics/' + img_name +'_%s.png' % page.number)  # store image as a PNG
        img_list.append('SavePics/' + img_name + '_%s.png' % page.number)
    return page_count, img_list
    


def uposs(filename):


    url_old='http://api.sdland-sea.com/api-lh-oss/lh-oss/uploadFile'
    files = {'file': open('SplitedPDF/'+str(filename)+'.pdf', 'rb')}
    r = requests.post(url_old, files=files)
    if r.status_code==200:
        # return r.json()['data']['url'],r.status_code
        return r.json()['url'],r.status_code #old url
    else:
        print('OSS Upload Server Error!')

def Huizhi(infor):
    url_huizhi='https://shipagentgateway.sdland-sea.com/online/api/services/app/EMC/BLDownloadSave'
    huizhi={"downPathList":infor}
    headers = {"Content-type": "application/json"}
    response = requests.post(url_huizhi, json=huizhi, headers=headers)
    if response.status_code==200:
        print('HuiZhi Information:',response.json())
        logger.info(response.json())
        logger.info("\n")
    else:
        print('Huizhi Server Error!')
        logger.info('Huizhi Server Error!')
        logger.info("\n")


def search_rename(pos,value,name):
    for i in range(len(value)):
        if 'EGLV' in value[i]:
            shr_pos = pos[i]
            height = pos[i][3][1] - pos[i][0][1]
            width = pos[i][1][0] - pos[i][0][0]
            for i in range(len(pos)):
                if shr_pos[0][0] - width / 2 < pos[i][0][0] < shr_pos[1][0] and shr_pos[3][1] - height/2 < pos[i][0][1] < shr_pos[3][1] +height*2 and len(value[i])==12 and value[i][1:5].isdigit():
                    if os.path.exists('SplitedPDF/'+str(name)):
                        os.rename('SplitedPDF/'+str(name),'SplitedPDF/'+str(value[i])+'.pdf')
                        oss_downlink,state_code=uposs(str(value[i]))

                        if state_code==200:
                            infor=[{'blno': str(value[i]), 'downloadPath': oss_downlink,"msg": "success!"}]
                            print('OSS Information:',infor)
                            logger.info(infor)
                            Huizhi(infor)
                        else:
                            print('Error!')
                            logger.info('OSS Error!')
                        os.remove('SplitedPDF/'+str(value[i])+'.pdf')
                        break
                    break
