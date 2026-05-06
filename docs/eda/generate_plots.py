"""EDA plot generator — docs/eda/ klasorune PNG'ler yazar."""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
import seaborn as sns
import os

os.makedirs(os.path.dirname(__file__), exist_ok=True)

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
df = pd.read_csv(os.path.join(ROOT, 'dataset.csv'))

seg_cols = [
    'chest_height_score', 'hip_length_score', 'thigh_length_score',
    'lower_leg_length_score', 'upper_arm_length_score',
    'forearm_length_score', 'neck_length_score',
]
score_cols = ['fat_score', 'muscle_score', 'height_score'] + seg_cols

GROUP_ORDER = ['underweight', 'normal', 'overweight', 'obese', 'athletic_lean', 'athletic_hyper']
PALETTE = {'male': '#4A90D9', 'female': '#E8687A'}
GROUP_COLORS = ['#A8D5BA', '#6BB5D6', '#F4A261', '#E76F51', '#74C69D', '#2D6A4F']

sns.set_theme(style='whitegrid', font_scale=1.05)
OUT = os.path.dirname(__file__)

# ── 1. Grup & Cinsiyet ───────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

counts = df.groupby(['group', 'gender']).size().unstack()
counts.loc[GROUP_ORDER].plot(
    kind='bar', ax=axes[0],
    color=[PALETTE['female'], PALETTE['male']],
    edgecolor='white', width=0.7,
)
axes[0].set_title('Grup x Cinsiyet Dagilimi')
axes[0].set_xlabel('')
axes[0].set_ylabel('Satir sayisi')
axes[0].tick_params(axis='x', rotation=30)
axes[0].legend(title='Cinsiyet')
for p in axes[0].patches:
    axes[0].annotate(
        f'{int(p.get_height()):,}',
        (p.get_x() + p.get_width() / 2, p.get_height() + 30),
        ha='center', fontsize=8,
    )

gender_counts = df['gender'].value_counts()
axes[1].pie(
    gender_counts, labels=gender_counts.index, autopct='%1.0f%%',
    colors=[PALETTE['female'], PALETTE['male']], startangle=90,
    wedgeprops={'edgecolor': 'white', 'linewidth': 2},
)
axes[1].set_title('Cinsiyet Orani')

plt.tight_layout()
plt.savefig(os.path.join(OUT, '01_group_gender.png'), dpi=130, bbox_inches='tight')
plt.close()
print('01 done')

# ── 2. Yas dagilimi ──────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

for g, c in PALETTE.items():
    axes[0].hist(
        df[df.gender == g]['age'], bins=range(14, 42),
        alpha=0.65, color=c, label=g, edgecolor='white',
    )
axes[0].set_title('Yas Dagilimi')
axes[0].set_xlabel('Yas')
axes[0].set_ylabel('Frekans')
axes[0].legend()
for x in [14, 19, 30]:
    axes[0].axvline(x, color='gray', linestyle='--', alpha=0.5, linewidth=1)

age_group = df.groupby('group')['age'].mean().loc[GROUP_ORDER]
axes[1].barh(range(len(GROUP_ORDER)), age_group.values, color=GROUP_COLORS, edgecolor='white')
axes[1].set_yticks(range(len(GROUP_ORDER)))
axes[1].set_yticklabels(GROUP_ORDER)
axes[1].set_title('Grup Bazli Ortalama Yas')
axes[1].set_xlabel('Ort. yas')
for i, v in enumerate(age_group.values):
    axes[1].text(v + 0.1, i, f'{v:.1f}', va='center', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(OUT, '02_age.png'), dpi=130, bbox_inches='tight')
plt.close()
print('02 done')

# ── 3. Height score ──────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

bins = np.linspace(0.19, 0.76, 40)
for g, c in PALETTE.items():
    axes[0].hist(
        df[df.gender == g]['height_score'], bins=bins,
        alpha=0.65, color=c, label=g, edgecolor='white',
    )
axes[0].axvline(0.20, color='red', linestyle='--', linewidth=1.2, label='alt sinir (0.20)')
axes[0].axvline(0.75, color='orange', linestyle='--', linewidth=1.2, label='eski ust sinir (0.75)')
axes[0].axvline(0.561, color='#E8687A', linestyle=':', linewidth=1.8, label='yeni kadin siniri (0.561)')
axes[0].set_title('Height Score Dagilimi')
axes[0].set_xlabel('height_score')
axes[0].set_ylabel('Frekans')
axes[0].legend(fontsize=8)

hs = df['height_score']
labels = ['Alt sinirda\n(0.20)', 'Aralikta', 'Ust sinirda\n(0.75)']
vals = [(hs == 0.20).sum(), ((hs > 0.20) & (hs < 0.75)).sum(), (hs == 0.75).sum()]
axes[1].bar(labels, vals, color=['#E76F51', '#6BB5D6', '#E8687A'], edgecolor='white')
axes[1].set_title('Height Score Sinir Yigilmasi')
axes[1].set_ylabel('Satir sayisi')
for i, v in enumerate(vals):
    axes[1].text(i, v + 80, f'{v:,}\n({v / len(df) * 100:.0f}%)', ha='center', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(OUT, '03_height_score.png'), dpi=130, bbox_inches='tight')
plt.close()
print('03 done')

# ── 4. Fat x Muscle scatter per group ────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
axes = axes.flatten()

for i, grp in enumerate(GROUP_ORDER):
    sub = df[df.group == grp]
    axes[i].scatter(
        sub['fat_score'], sub['muscle_score'],
        alpha=0.15, s=4,
        c=sub['gender'].map(PALETTE),
    )
    axes[i].set_title(grp, fontsize=10)
    axes[i].set_xlabel('fat_score', fontsize=8)
    axes[i].set_ylabel('muscle_score', fontsize=8)
    axes[i].set_xlim(-0.05, 1.05)
    axes[i].set_ylim(-0.05, 1.05)

handles = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=7, label=g)
    for g, c in PALETTE.items()
]
fig.legend(handles=handles, loc='lower right', title='Cinsiyet')
plt.suptitle('Fat x Muscle Score — Gruba Gore', y=1.01, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT, '04_fat_muscle_scatter.png'), dpi=130, bbox_inches='tight')
plt.close()
print('04 done')

# ── 5. Segment spread ────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

spread = df[seg_cols].max(axis=1) - df[seg_cols].min(axis=1)
axes[0].hist(spread, bins=60, color='#6BB5D6', edgecolor='white')
axes[0].axvline(0.30, color='red', linestyle='--', linewidth=1.5, label='SEG_MAX_DEV=0.30')
axes[0].set_title('Segment Score Spread Dagilimi')
axes[0].set_xlabel('max - min (7 segment)')
axes[0].set_ylabel('Frekans')
axes[0].legend()
at_cap = (spread >= 0.2999).sum()
axes[0].text(
    0.05, 0.85, f'Tavanda: {at_cap:,} ({at_cap / len(df) * 100:.0f}%)',
    transform=axes[0].transAxes, fontsize=10,
    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7),
)

seg_short = ['chest_h', 'hip_l', 'thigh_l', 'lower_leg_l', 'upper_arm_l', 'forearm_l', 'neck_l']
axes[1].boxplot(
    [df[c].values for c in seg_cols], labels=seg_short,
    patch_artist=True,
    boxprops=dict(facecolor='#A8D5BA', alpha=0.7),
    medianprops=dict(color='#E76F51', linewidth=2),
)
axes[1].set_title('Segment Score Dagilimi (boxplot)')
axes[1].set_ylabel('Score')
axes[1].axhline(0.5, color='gray', linestyle='--', alpha=0.5)
axes[1].tick_params(axis='x', rotation=20)

plt.tight_layout()
plt.savefig(os.path.join(OUT, '05_segment_spread.png'), dpi=130, bbox_inches='tight')
plt.close()
print('05 done')

# ── 6. Korelasyon isı haritası ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 8))

corr = df[score_cols].corr()
short = ['fat', 'muscle', 'height', 'chest_h', 'hip_l', 'thigh_l', 'lower_leg_l', 'upper_arm_l', 'forearm_l', 'neck_l']
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(
    corr, mask=mask, annot=True, fmt='.2f', cmap='RdYlGn',
    center=0, vmin=-1, vmax=1,
    xticklabels=short, yticklabels=short,
    linewidths=0.5, ax=ax, cbar_kws={'shrink': 0.8},
)
ax.set_title('Score Sutunlari Korelasyon Matrisi', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT, '06_correlation.png'), dpi=130, bbox_inches='tight')
plt.close()
print('06 done')

# ── 7. Training pattern ──────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

tp_order = ['balanced', 'upper_dominant', 'lower_dominant', 'push_dominant', 'pull_dominant']
tp_athletic = df[df.group.isin(['athletic_lean', 'athletic_hyper'])]
tp_counts = tp_athletic.groupby(['group', 'training_pattern']).size().unstack(fill_value=0)
tp_counts[tp_order].plot(kind='bar', ax=axes[0], edgecolor='white', width=0.7)
axes[0].set_title('Training Pattern (Atletik Gruplar)')
axes[0].set_xlabel('')
axes[0].set_ylabel('Satir sayisi')
axes[0].tick_params(axis='x', rotation=0)
axes[0].legend(fontsize=8, title='Pattern')

tp_all = df['training_pattern'].value_counts().loc[tp_order]
tp_colors = ['#6BB5D6', '#F4A261', '#E8687A', '#74C69D', '#9B59B6']
axes[1].bar(tp_order, tp_all.values, color=tp_colors, edgecolor='white')
axes[1].set_title('Training Pattern - Tum Veri')
axes[1].set_ylabel('Satir sayisi')
axes[1].tick_params(axis='x', rotation=20)
for i, v in enumerate(tp_all.values):
    axes[1].text(i, v + 100, f'{v:,}', ha='center', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(OUT, '07_training_pattern.png'), dpi=130, bbox_inches='tight')
plt.close()
print('07 done')

# ── 8. Fat & Muscle boxplot per group ────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

for ax, col, title in [
    (axes[0], 'fat_score', 'Fat Score'),
    (axes[1], 'muscle_score', 'Muscle Score'),
]:
    data = [df[df.group == g][col].values for g in GROUP_ORDER]
    bp = ax.boxplot(
        data, patch_artist=True, labels=GROUP_ORDER,
        medianprops=dict(color='black', linewidth=2),
    )
    for patch, color in zip(bp['boxes'], GROUP_COLORS):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_title(title + ' - Gruba Gore')
    ax.set_ylabel(col)
    ax.tick_params(axis='x', rotation=30)

plt.tight_layout()
plt.savefig(os.path.join(OUT, '08_fat_muscle_boxplot.png'), dpi=130, bbox_inches='tight')
plt.close()
print('08 done')

# ── 9. Her segment score ayrı ayrı ──────────────────────────────────────────
seg_labels_full = [
    'chest_height', 'hip_length', 'thigh_length', 'lower_leg_length',
    'upper_arm_length', 'forearm_length', 'neck_length',
]

fig, axes = plt.subplots(2, 4, figsize=(16, 8))
axes = axes.flatten()

for i, (col, label) in enumerate(zip(seg_cols, seg_labels_full)):
    ax = axes[i]
    for g, c in PALETTE.items():
        ax.hist(df[df.gender == g][col], bins=40, alpha=0.6, color=c, label=g, edgecolor='white')
    ax.axvline(df[col].mean(), color='black', linestyle='--', linewidth=1.2,
               label=f'ort={df[col].mean():.2f}')
    ax.set_title(label, fontsize=10)
    ax.set_xlabel('score')
    ax.set_ylabel('frekans')
    ax.set_xlim(0, 1)
    ax.legend(fontsize=7)

# Boş 8. hücreye özet istatistik tablosu
ax8 = axes[7]
ax8.axis('off')
stats = df[seg_cols].describe().loc[['mean', 'std', 'min', 'max']].T.round(3)
stats.index = seg_labels_full
col_labels = ['mean', 'std', 'min', 'max']
table = ax8.table(
    cellText=stats.values,
    rowLabels=stats.index,
    colLabels=col_labels,
    loc='center',
    cellLoc='center',
)
table.auto_set_font_size(False)
table.set_fontsize(8)
table.scale(1.2, 1.5)
ax8.set_title('Ozet Istatistikler', fontsize=10)

plt.suptitle('Segment Score Dagilimi — Her Segment Ayri Ayri', y=1.01, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT, '09_segment_individual.png'), dpi=130, bbox_inches='tight')
plt.close()
print('09 done')

# ── 10. Segment score'lar grup bazında ───────────────────────────────────────
fig, axes = plt.subplots(2, 4, figsize=(16, 8))
axes = axes.flatten()

for i, (col, label) in enumerate(zip(seg_cols, seg_labels_full)):
    ax = axes[i]
    data = [df[df.group == g][col].values for g in GROUP_ORDER]
    bp = ax.boxplot(
        data, patch_artist=True, tick_labels=GROUP_ORDER,
        medianprops=dict(color='black', linewidth=1.5),
    )
    for patch, color in zip(bp['boxes'], GROUP_COLORS):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_title(label, fontsize=10)
    ax.set_ylabel('score')
    ax.tick_params(axis='x', rotation=35, labelsize=7)
    ax.set_ylim(0, 1)

axes[7].axis('off')

plt.suptitle('Segment Score — Grup Bazli Dagilim', y=1.01, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT, '10_segment_by_group.png'), dpi=130, bbox_inches='tight')
plt.close()
print('10 done')

SOMA_ORDER_F  = ['hourglass', 'pear', 'rectangle', 'apple']
SOMA_ORDER_M  = ['v_shape', 'rectangle', 'apple']
SOMA_ORDER    = ['hourglass', 'pear', 'rectangle', 'apple', 'v_shape']
SOMA_COLORS   = {
    'hourglass': '#E8687A', 'pear': '#F4A261', 'rectangle': '#6BB5D6',
    'apple': '#74C69D',     'v_shape': '#9B59B6',
}

# ── 11. Somatotip dağılımı ────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# Genel dağılım bar
soma_counts = df['somatotype'].value_counts().reindex(SOMA_ORDER, fill_value=0)
axes[0].bar(
    SOMA_ORDER, soma_counts.values,
    color=[SOMA_COLORS[s] for s in SOMA_ORDER], edgecolor='white',
)
axes[0].set_title('Somatotip Dagilimi (Toplam)')
axes[0].set_ylabel('Satir sayisi')
axes[0].tick_params(axis='x', rotation=20)
for i, v in enumerate(soma_counts.values):
    axes[0].text(i, v + 80, f'{v:,}\n({v/len(df)*100:.0f}%)', ha='center', fontsize=8)

# Kadın pie
female_soma = df[df.gender == 'female']['somatotype'].value_counts().reindex(SOMA_ORDER_F, fill_value=0)
axes[1].pie(
    female_soma.values, labels=SOMA_ORDER_F, autopct='%1.0f%%',
    colors=[SOMA_COLORS[s] for s in SOMA_ORDER_F],
    startangle=90, wedgeprops={'edgecolor': 'white', 'linewidth': 2},
)
axes[1].set_title('Kadin Somatotip Orani')

# Erkek pie
male_soma = df[df.gender == 'male']['somatotype'].value_counts().reindex(SOMA_ORDER_M, fill_value=0)
axes[2].pie(
    male_soma.values, labels=SOMA_ORDER_M, autopct='%1.0f%%',
    colors=[SOMA_COLORS[s] for s in SOMA_ORDER_M],
    startangle=90, wedgeprops={'edgecolor': 'white', 'linewidth': 2},
)
axes[2].set_title('Erkek Somatotip Orani')

plt.tight_layout()
plt.savefig(os.path.join(OUT, '11_somatotype_dist.png'), dpi=130, bbox_inches='tight')
plt.close()
print('11 done')

# ── 12. Shape score dağılımı ──────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Violin: shape_score per somatotype
violin_data = [df[df.somatotype == s]['shape_score'].values for s in SOMA_ORDER]
vp = axes[0].violinplot(violin_data, positions=range(len(SOMA_ORDER)), showmedians=True)
for i, (body, s) in enumerate(zip(vp['bodies'], SOMA_ORDER)):
    body.set_facecolor(SOMA_COLORS[s])
    body.set_alpha(0.7)
vp['cmedians'].set_color('black')
vp['cmedians'].set_linewidth(2)
axes[0].set_xticks(range(len(SOMA_ORDER)))
axes[0].set_xticklabels(SOMA_ORDER, rotation=20)
axes[0].set_title('Shape Score Dagilimi — Somatotipe Gore')
axes[0].set_ylabel('shape_score')
axes[0].set_ylim(0, 1.05)

# Scatter: fat x muscle, somatotype renkli (subsample)
sub = df.sample(n=min(4000, len(df)), random_state=42)
for s in SOMA_ORDER:
    d = sub[sub.somatotype == s]
    axes[1].scatter(d['fat_score'], d['muscle_score'],
                    alpha=0.25, s=5, color=SOMA_COLORS[s], label=s)
axes[1].set_title('Fat x Muscle — Somatotip Renkleri')
axes[1].set_xlabel('fat_score')
axes[1].set_ylabel('muscle_score')
axes[1].legend(markerscale=3, fontsize=8, title='Somatotip')

plt.tight_layout()
plt.savefig(os.path.join(OUT, '12_shape_score.png'), dpi=130, bbox_inches='tight')
plt.close()
print('12 done')

# ── 13. Fat x Muscle per somatotype ──────────────────────────────────────────
fig, axes = plt.subplots(1, 5, figsize=(18, 4), sharey=True)

for ax, s in zip(axes, SOMA_ORDER):
    sub = df[df.somatotype == s]
    ax.scatter(
        sub['fat_score'], sub['muscle_score'],
        alpha=0.15, s=4, c=sub['gender'].map(PALETTE),
    )
    ax.set_title(f'{s}\n(n={len(sub):,})', fontsize=9)
    ax.set_xlabel('fat_score', fontsize=8)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
axes[0].set_ylabel('muscle_score')

handles = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=7, label=g)
    for g, c in PALETTE.items()
]
fig.legend(handles=handles, loc='lower right', title='Cinsiyet')
plt.suptitle('Fat x Muscle — Somatotip Bazli', y=1.02, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT, '13_somatotype_fatmuscle.png'), dpi=130, bbox_inches='tight')
plt.close()
print('13 done')

print('\nTum plotlar docs/eda/ klasorune kaydedildi.')
