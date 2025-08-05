import os
import sys
import requests
import fitz
import PyPDF2
import aiofiles
import logging
import asyncio
from collections import defaultdict
from paddleocr import PaddleOCR
from logutils import *

# 日志配置，输出到标准输出
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
t_logger = logging.getLogger('pdf_processor')
# 降低 OCR 库日志
logging.getLogger('ppocr').setLevel(logging.INFO)

ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ch",
    workers=12,
    use_gpu=True,
    det_limit_side_len=1216,
    use_multiprocess=True
)

async def save_file(File, filename):
    """异步保存上传文件到 UploadFile 目录并记录日志"""
    async with aiofiles.open(os.path.join('UploadFile', filename), 'wb') as out_file:
        content = await File.read()
        await out_file.write(content)
    t_logger.info('文件上传成功: %s', filename)


def pdf_img(pdf_path, img_name):
    """将 PDF 渲染为图片列表"""
    img_list = []
    doc = fitz.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img_path = f"SavePics/{img_name}_{page.number}.png"
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        pix.save(img_path)
        img_list.append(img_path)
    return doc.page_count, img_list


def detect_img(img_path):
    """OCR 识别单张图片"""
    result = ocr.ocr(img_path, cls=False)
    pos, vals = [], []
    for line in result[0]:
        pos.append(line[0]); vals.append(line[1][0])
    return pos, vals


def uposs(code):
    """上传合并后的 PDF 到 OSS 并记录日志"""
    url_new = 'http://lh-oss.sdland-sea.com/lh-oss/uploadFile'
    merged_path = f'MergedPDF/{code}.pdf'
    t_logger = logging.getLogger(__name__)
    t_logger.info('上传到 OSS 开始: %s', merged_path)

    # Check if file exists and is readable
    if not os.path.isfile(merged_path):
        t_logger.error('文件不存在: %s', merged_path)
        return None, 0
    if not os.access(merged_path, os.R_OK):
        t_logger.error('文件不可读: %s', merged_path)
        return None, 0

    try:
        with open(merged_path, 'rb') as f:
            t_logger.debug('文件大小: %d 字节', os.path.getsize(merged_path))
            # Specify filename and Content-Type for MinIO
            files = {'file': (f'{code}.pdf', f, 'application/pdf')}
            r = requests.post(url_new, files=files, timeout=30)
        
        status_code = r.json().get('code', r.status_code)
        oss_url = r.json().get('data', {}).get('url', '')
        
        if status_code == 200:
            try:
                oss_url = r.json().get('data', {}).get('url', '')
                t_logger.info('OSS 上传成功: code=%s, url=%s', code, oss_url)
                print(f"OSS 上传成功: {oss_url}")
                return oss_url, status_code
            except ValueError:
                t_logger.error('响应不是有效的 JSON: %s', status_code)
                return None, status_code
        else:
            t_logger.error('OSS 上传失败: code=%s, 状态=%s', code, status_code)
            return None, r.status_code
    except requests.RequestException as e:
        t_logger.error('HTTP 请求失败: code=%s, 错误=%s', code, str(e))
        return None, 0
    except Exception as e:
        t_logger.error('意外错误: code=%s, 错误=%s', code, str(e))
        return None, 0

def Huizhi(info):
    """回执上传结果到回执系统，并记录日志"""
    url = 'https://shipagentgateway.sdland-sea.com/online/api/services/app/EMC/BLDownloadSave'
    t_logger.info('发送回执信息: %s', info)
    resp = requests.post(url, json={"downPathList": info}, headers={"Content-type": "application/json"})
    t_logger.info('回执系统返回状态: %s, 内容: %s', resp.status_code, resp.text)
    if resp.status_code == 200:
        t_logger.info('回执成功: %s', resp.json())
    else:
        t_logger.error('回执失败: payload=%s, 状态=%s', info, resp.status_code)


def handle_file(filename):
    """处理单个上传文件：拆分、合并、上传、清理"""
    upload_dir, split_dir, merged_dir = 'UploadFile', 'SplitedPDF', 'MergedPDF'
    os.makedirs(split_dir, exist_ok=True)
    os.makedirs(merged_dir, exist_ok=True)

    base = os.path.splitext(filename)[0]
    path = os.path.join(upload_dir, filename)
    t_logger.info('开始处理文件: %s', filename)

    # 拆分
    counters = defaultdict(int)
    page_count, img_list = pdf_img(path, base)
    reader = PyPDF2.PdfFileReader(open(path, 'rb'))
    split_files = []
    for i in range(page_count):
        page = reader.getPage(i)
        pos, vals = detect_img(img_list[i])
        os.remove(img_list[i])

        code1 = next(( ''.join(ch for ch in v.split('EGLV',1)[1] if ch.isdigit())
                       for v in vals if 'EGLV' in v and len(v)>10), None)
        code2 = None
        for j, v in enumerate(vals):
            if 'EGLV' not in v: continue
            shr = pos[j]
            h, w = shr[3][1] - shr[0][1], shr[1][0] - shr[0][0]
            for cand_idx, cand in enumerate(vals):
                x0, y0 = pos[cand_idx][0]
                if (shr[0][0] - w/2 < x0 < shr[1][0] and
                    shr[3][1] - h/2 < y0 < shr[3][1] + h*2 and
                    len(cand) == 12 and cand[1:5].isdigit()):
                    code2 = cand
                    break
            if code2:
                break

        code = code2 or code1 or base
        counters[code] += 1
        idx = counters[code]
        split_name = f"{code}_{idx}.pdf"
        split_path = os.path.join(split_dir, split_name)
        writer = PyPDF2.PdfFileWriter()
        writer.addPage(page)
        with open(split_path, 'wb') as fo:
            writer.write(fo)
        split_files.append(split_name)
        t_logger.info('已生成拆分文件: %s', split_name)

    # 合并并上传
    groups = defaultdict(list)
    for name in split_files:
        code_key, idx = os.path.splitext(name)[0].rsplit('_', 1)
        groups[code_key].append((int(idx), name))

    for code_key, items in groups.items():
        items.sort(key=lambda x: x[0])
        merger = PyPDF2.PdfFileMerger()
        for _, fn in items:
            merger.append(os.path.join(split_dir, fn))
        merged_file = os.path.join(merged_dir, f"{code_key}.pdf")
        with open(merged_file, 'wb') as mo:
            merger.write(mo)
        merger.close()
        t_logger.info('已生成合并文件: %s', merged_file)

        # 删除拆分文件
        for _, fn in items:
            os.remove(os.path.join(split_dir, fn))
        t_logger.info('已删除拆分文件, 代码: %s', code_key)

        # 上传并回执
        oss_url, status = uposs(code_key)
        if status == 200 and oss_url:
            info = [{'blno': code_key, 'downloadPath': oss_url, 'msg': 'success!'}]
            print('上传成功，回执信息:', info)
            t_logger.info('上传成功，回执信息: %s', info)
            Huizhi(info)
            t_logger.info('准备删除本地合并文件: %s', merged_file)
            os.remove(merged_file)
            t_logger.info('已删除本地合并文件: %s', merged_file)
        else:
            t_logger.error('上传失败, 合并文件保留: %s', merged_file)

    # 删除源文件
    os.remove(path)
    t_logger.info('已删除源文件: %s', filename)

async def process_file(filename):
    """异步处理单个文件"""
    await asyncio.to_thread(handle_file, filename)

async def main():
    """并行处理 UploadFile 中的所有 PDF"""
    upload_dir = 'UploadFile'
    tasks = []
    for fn in os.listdir(upload_dir):
        if fn.lower().endswith('.pdf'):
            tasks.append(asyncio.create_task(process_file(fn)))
    if tasks:
        await asyncio.gather(*tasks)
