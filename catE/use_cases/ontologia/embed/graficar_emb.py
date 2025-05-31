import pandas as pd
import plotly.express as px

# Cargar datos
df = pd.read_csv('embedding_wandb.csv')

# Opcional: Filtrar outliers (ejemplo: eliminar puntos fuera del percentil 99%)
low = df[['x', 'y', 'z']].quantile(0.01)
high = df[['x', 'y', 'z']].quantile(0.99)
df_filtered = df[~(df[['x', 'y', 'z']] < low) | (df[['x', 'y', 'z']] > high).any(axis=1)]

# Graficar
fig = px.scatter_3d(
    df_filtered,  # Usar df si no quieres filtrar
    x='x', y='y', z='z',
    color='label',
    title='Embeddings 3D (Proyecto catE)',
    hover_name='label',
    width=1000,
    height=800
)

# Ajustar diseño
fig.update_layout(
    scene=dict(
        xaxis_title='X',
        yaxis_title='Y',
        zaxis_title='Z',
        # Opcional: Forzar ejes con rangos similares
        xaxis=dict(range=[-60, 60]),
        yaxis=dict(range=[-60, 60]),
        zaxis=dict(range=[-60, 60]),
    ),
    margin=dict(l=0, r=0, b=0, t=30)
)

# Mostrar figura
fig.show()

# Guardar como HTML (opcional)
fig.write_html("embeddings_3d_interactive.html")