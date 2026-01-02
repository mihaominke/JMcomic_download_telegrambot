
import os, re, img2pdf
from PIL import Image

def all2PDF(input_folder, output_folder, output_name, max_pdf_size_mb=45):
    os.makedirs(output_folder, exist_ok=True)
    image_paths = []
    try:
        entries = os.listdir(input_folder)
    except FileNotFoundError:
        raise Exception(f"未找到漫画目录：{input_folder}")

    def sort_key(name):
        import re
        nums = re.findall(r'\d+', name)
        return int(nums[0]) if nums else name

    subdirs = sorted([d for d in entries if os.path.isdir(os.path.join(input_folder, d))], key=sort_key)
    files = sorted([f for f in entries if os.path.isfile(os.path.join(input_folder, f))])

    if subdirs:
        for sub in subdirs:
            sub_path = os.path.join(input_folder, sub)
            for fname in sorted(os.listdir(sub_path), key=sort_key):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    image_paths.append(os.path.join(sub_path, fname))
    for fname in files:
        if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            image_paths.append(os.path.join(input_folder, fname))

    if not image_paths:
        raise Exception(f"未找到图片，请检查下载是否成功，路径：{input_folder}")

    max_size_bytes = max_pdf_size_mb * 1024 * 1024
    batch, batch_size, part = [], 0, 1
    pdf_paths = []

    def save_batch(img_list, index):
        if not img_list:
            return
        pdf_name = f"{output_name}_part{index}.pdf" if len(image_paths) > len(img_list) else f"{output_name}.pdf"
        pdf_path = os.path.join(output_folder, pdf_name)
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(img_list))
        size_mb = os.path.getsize(pdf_path) / 1024 / 1024
        print(f"✅ 生成 PDF: {pdf_path} ({size_mb:.2f} MB)")
        pdf_paths.append(pdf_path)

    for img_path in image_paths:
        size = os.path.getsize(img_path)
        if batch_size + size > max_size_bytes and batch:
            save_batch(batch, part)
            part += 1
            batch, batch_size = [], 0
        batch.append(img_path)
        batch_size += size

    if batch:
        save_batch(batch, part)

    if not pdf_paths:
        print("⚠️ img2pdf 转换失败，尝试 Pillow 回退。")
        first_image = Image.open(image_paths[0])
        if first_image.mode != "RGB":
            first_image = first_image.convert("RGB")
        pdf_images = []
        for img_path in image_paths[1:]:
            try:
                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                pdf_images.append(img)
            except:
                continue
        pdf_path = os.path.join(output_folder, f"{output_name}.pdf")
        first_image.save(pdf_path, "PDF", save_all=True, append_images=pdf_images)
        pdf_paths = [pdf_path]
        print(f"✅ Pillow 成功生成 PDF: {pdf_path}")

    return pdf_paths
