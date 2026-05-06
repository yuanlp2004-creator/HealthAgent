import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC']
matplotlib.rcParams['axes.unicode_minus'] = False

schemes = [
    'PaddleOCR\nPP-OCRv4\n(CPU, 通用中英)',
    'PaddleOCR\n+ CLAHE/\n反色三变体',
    '百度云accurate\n通用OCR',
    '百度云numbers\n数字OCR\n+ bbox过滤',
    '分类先行\n双通路\n(本文方案)'
]

accuracy = [16.7, 20.0, 16.7, 3.3, 100.0]
time_cost = [1.54, 1.97, 0.64, 0.86, 1.00]

colors = ['#7f7f7f', '#7f7f7f', '#7f7f7f', '#7f7f7f', '#1f77b4']
x = np.arange(len(schemes))
width = 0.55

fig, ax1 = plt.subplots(figsize=(10, 5.5))

bars = ax1.bar(x, accuracy, width, color=colors, edgecolor='white', linewidth=0.5, zorder=3)
ax1.set_ylabel('字段准确率 (%)', fontsize=12)
ax1.set_ylim(0, 115)
ax1.set_yticks(np.arange(0, 121, 20))

for bar, val in zip(bars, accuracy):
    y_pos = val + 2.5
    ax1.text(bar.get_x() + bar.get_width() / 2, y_pos, f'{val}%',
             ha='center', va='bottom', fontsize=12, fontweight='bold',
             color='#1f77b4' if val == 100.0 else '#333333')

ax2 = ax1.twinx()
line = ax2.plot(x, time_cost, 'o-', color='#333333', linewidth=2.5,
                markersize=10, markerfacecolor='#333333', zorder=4)
ax2.set_ylabel('平均耗时 (s)', fontsize=12)
ax2.set_ylim(0, 2.4)
ax2.set_yticks(np.arange(0, 2.6, 0.4))

for i, (xi, tc) in enumerate(zip(x, time_cost)):
    ax2.annotate(f'{tc}s', (xi, tc), textcoords="offset points",
                 xytext=(5, 14), ha='center', fontsize=11, color='#333333', fontweight='bold')

ax1.set_xticks(x)
ax1.set_xticklabels(schemes, fontsize=9)
ax1.set_title('OCR方案对比实验结果', fontsize=15, fontweight='bold', pad=16)
ax1.set_xlim(-0.5, len(schemes) - 0.5)
ax1.grid(axis='y', alpha=0.3, zorder=0)
ax1.set_axisbelow(True)

fig.tight_layout()
fig.savefig(r'D:\HealthAgent\pic\fig_ocr_compare.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print('Saved to D:/HealthAgent/pic/fig_ocr_compare.png')
