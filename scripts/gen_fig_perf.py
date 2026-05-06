import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

FONT_LABEL = 11
FONT_TICK = 10
FONT_LEGEND = 9
FONT_ANNO = 10
BAR_H = 0.28

ops_s = ['百度云通用\nOCR调用', 'VLM直接识别\n(LCD路径)', 'SSE首Token']
avg_s = [0.64, 1.05, 0.70]
p95_s = [1.0, 2.0, 1.5]
nfr_s = [3.0, 3.0, 3.0]

ops_ms = ['血压列表分页查询\n(100条)', '统计聚合查询\n(90天)']
avg_ms = [45, 32]
p95_ms = [78, 55]
nfr_ms = [100, 100]

fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(14, 5),
    gridspec_kw={'width_ratios': [1, 1.15]}
)

# --- Left panel: seconds ---
y_s = np.arange(len(ops_s))

bars_avg = ax1.barh(y_s + BAR_H, avg_s, BAR_H, color='#1f77b4', edgecolor='white', label='平均延迟')
bars_p95 = ax1.barh(y_s, p95_s, BAR_H, color='#ff7f0e', edgecolor='white', label='P95延迟')
bars_nfr = ax1.barh(y_s - BAR_H, nfr_s, BAR_H, color='#d3d3d3', edgecolor='white', label='NFR目标 (≤3s)')

for bar, val in zip(bars_avg, avg_s):
    ax1.text(val + 0.06, bar.get_y() + bar.get_height() / 2, f'{val}s',
             va='center', fontsize=FONT_ANNO, fontweight='bold', color='#1f77b4')
for bar, val in zip(bars_p95, p95_s):
    ax1.text(val + 0.06, bar.get_y() + bar.get_height() / 2, f'{val}s',
             va='center', fontsize=FONT_ANNO, fontweight='bold', color='#ff7f0e')

ax1.set_ylim(-0.6, 2.6)
ax1.set_yticks(y_s)
ax1.set_yticklabels(ops_s, fontsize=FONT_TICK)
ax1.set_xlim(0, 4.2)
ax1.set_xlabel('延迟 (秒)', fontsize=FONT_LABEL)
ax1.tick_params(axis='y', labelsize=FONT_TICK)
ax1.tick_params(axis='x', labelsize=FONT_TICK)
ax1.legend(loc='lower right', fontsize=FONT_LEGEND, framealpha=0.9)
ax1.grid(axis='x', alpha=0.25)
ax1.set_axisbelow(True)

# --- Right panel: milliseconds ---
y_m = np.arange(len(ops_ms)) + 0.5  # center within same y-range as left panel

bars_avg2 = ax2.barh(y_m + BAR_H, avg_ms, BAR_H, color='#1f77b4', edgecolor='white')
bars_p952 = ax2.barh(y_m, p95_ms, BAR_H, color='#ff7f0e', edgecolor='white')
bars_nfr2 = ax2.barh(y_m - BAR_H, nfr_ms, BAR_H, color='#d3d3d3', edgecolor='white')

for bar, val in zip(bars_avg2, avg_ms):
    ax2.text(val + 1.8, bar.get_y() + bar.get_height() / 2, f'{val}ms',
             va='center', fontsize=FONT_ANNO, fontweight='bold', color='#1f77b4')
for bar, val in zip(bars_p952, p95_ms):
    ax2.text(val + 1.8, bar.get_y() + bar.get_height() / 2, f'{val}ms',
             va='center', fontsize=FONT_ANNO, fontweight='bold', color='#ff7f0e')

ax2.set_ylim(-0.6, 2.6)
ax2.set_yticks(y_m)
ax2.set_yticklabels(ops_ms, fontsize=FONT_TICK)
ax2.set_xlim(0, 130)
ax2.set_xlabel('延迟 (毫秒)', fontsize=FONT_LABEL)
ax2.tick_params(axis='y', labelsize=FONT_TICK)
ax2.tick_params(axis='x', labelsize=FONT_TICK)
ax2.grid(axis='x', alpha=0.25)
ax2.set_axisbelow(True)

from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#1f77b4', label='平均延迟'),
    Patch(facecolor='#ff7f0e', label='P95延迟'),
    Patch(facecolor='#d3d3d3', label='NFR目标 (≤100ms)'),
]
ax2.legend(handles=legend_elements, loc='lower right', fontsize=FONT_LEGEND, framealpha=0.9)

fig.suptitle('关键操作性能基准', fontsize=15, fontweight='bold', y=1.01)
fig.tight_layout()
fig.savefig(r'D:\HealthAgent\pic\pic3.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print('Saved to D:/HealthAgent/pic/pic3.png')
