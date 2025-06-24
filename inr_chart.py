import matplotlib.pyplot as plt
import io
from PIL import Image
import base64

def generate_inr_chart(dates, inr_values):
    fig, ax = plt.subplots(figsize=(8, 4))

    # ตัดค่าที่เกิน 5.5 แต่ให้วาดจุดไว้เหนือ 5.5
    clipped_values = [min(v, 5.5) for v in inr_values]

    # วาดกราฟเส้น
    ax.plot(dates, clipped_values, marker="o", color="#007bff", label="INR")

    # เติม label ที่จุด
    for i, (x, y, raw_y) in enumerate(zip(dates, clipped_values, inr_values)):
        ax.text(x, y + 0.15, f"{raw_y:.1f}", ha="center", fontsize=10, color="black")
        # ถ้า INR >= 6 ให้ใช้จุดแดง
        if raw_y >= 6:
            ax.plot(x, y, marker="o", color="red", markersize=10)

    # พื้นหลังสีเขียวระหว่าง INR 2.0–3.5
    ax.axhspan(2.0, 3.5, facecolor='green', alpha=0.1)

    # ตั้ง y scale เริ่มที่ 0.5 ถึง 5.5
    ax.set_ylim(0.5, 6.2)
    ax.set_yticks([i * 0.5 for i in range(1, 12)])
    ax.set_ylabel("ค่า INR")
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=45)
    ax.set_title("กราฟ INR")

    plt.tight_layout()

    # แปลงเป็น buffer image
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return buf