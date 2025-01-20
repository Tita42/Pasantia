# README - Pasos a Seguir para Implementar CatE

## Introducción

Soy estudiante de la Facultad de Ingeniería (FING) y actualmente estoy realizando una pasantía en el marco del proyecto "Aplicación de un enfoque neuro simbólico basado en grafos para enriquecer ontologías". Este README documenta los avances realizados durante este tiempo y proporciona una guía detallada de los pasos necesarios para replicar y continuar este trabajo. Aunque no logré completar todas las etapas planificadas, como el entrenamiento final del modelo, avancé significativamente en la configuración del entorno, la preparación de los datos y el entendimiento de las herramientas implicadas.

## Requisitos Previos

1. **Hardware**
   - Computadora con soporte CUDA (preferiblemente con una tarjeta NVIDIA compatible).
   - Alternativamente, se puede usar CPU, aunque el rendimiento será significativamente más lento.

2. **Software Necesario**
   - **Sistema operativo:** Windows.
   - **Python:** Versión 3.9 o superior.
   - **Java:** Instalar JDK (versión 8.0.152 y superior) y configurar la variable de entorno `JAVA_HOME`.
   - **Anaconda:** Para manejar los entornos virtuales.
   - **Eclipse IDE:** Para trabajar con OWL2Vec* y configurar proyectos Maven.
   - **Visual Studio Build Tools:** Para compilar dependencias en Python.

3. **Librerías y Herramientas**
   - **CatE**: Herramienta principal para embeddings.
   - **mOWL**: Biblioteca para manejo de ontologías OWL.
   - **OWL2Vec***: Para generar los archivos necesarios para entrenamiento.
   - **PyTorch:** Para el entrenamiento de la red neuronal.
   - **SLF4J:** Dependencia para trabajar con OWLAPI.

## Instalación

### 1. Configuración del Entorno

#### a. **Instalar y Configurar PyTorch**
1. Verificar la versión de CUDA instalada con el comando:
   ```bash
   nvidia-smi
   ```
2. Ir a [PyTorch](https://pytorch.org/get-started/locally/) y descargar la versión correspondiente.
3. Instalar con `pip` o desde la PowerShell de Anaconda:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

#### b. **Instalar OWLAPI y SLF4J**
1. Descargar OWLAPI desde [Maven Repository](https://mvnrepository.com/artifact/net.sourceforge.owlapi/owlapi-distribution).
2. Descargar SLF4J desde [Maven Repository](https://repo1.maven.org/maven2/org/slf4j/).
3. Configurar el archivo `run_cat_completion.py` para incluir las rutas necesarias:
   ```python
   mowl.init_jvm("C:\\Program Files\\Java\\jdk-23\\bin\\server\\jvm.dll", "-ea", "-Xmx10g")
   ```

#### c. **Configurar Anaconda**
1. Crear entornos para las herramientas:

   - **mOWL:**
     ```bash
     conda create -n mowl_env
     conda activate mowl_env
     pip install git+https://github.com/bio-ontology-research-group/mowl
     pip install torch gensim==4.3.0 JPype1==1.5.1 pykeen==1.11.0 scipy<1.15.0
     ```

   - **CatE:**
     ```bash
     git clone https://github.com/bio-ontology-research-group/CatE.git
     cd CatE
     conda env create -f environment.yml
     conda activate cate
     pip install wandb --upgrade
     ```

   - **OWL2Vec***:
     ```bash
     git clone https://github.com/KRR-Oxford/OWL2Vec-Star.git
     cd OWL2Vec-Star
     conda create -n owl2vec python=3.8
     conda activate owl2vec
     pip install -r requirements_owl2vec.txt
     ```

#### d. **Configurar Eclipse y Maven**
1. Crear un proyecto Maven en Eclipse para OWL2Vec*.
2. Configurar dependencias en el archivo `pom.xml`. Por ejemplo:
   ```xml
   <dependency>
       <groupId>javax.xml.bind</groupId>
       <artifactId>jaxb-api</artifactId>
       <version>2.3.1</version>
   </dependency>
   ```
3. Asegurarse de que `JRDFox` esté configurado correctamente siguiendo las instrucciones del repositorio.

---

## Generación de Archivos Necesarios

### 1. Crear el Archivo `edgelist`
1. Navegar a la carpeta `src` de CatE.
2. Ejecutar el script de proyección del grafo:
   ```bash
   python cat_projector.py ruta/a/catE/use_cases/ontologia/data/ontologia.owl
   ```

### 2. Eliminar Morfismos Innecesarios
1. Editar el archivo generado `ontologia.edgelist` para asegurarse de que tenga codificación UTF-8.
2. Ejecutar:
   ```bash
   python remove_obvious_morphisms.py ruta/a/catE/use_cases/ontologia/data/ontologia.edgelist
   ```

### 3. Generar Archivos de Entrenamiento, Validación y Prueba
1. Configurar y ejecutar el archivo `ClassAssertion_NormalSplit.java` desde Eclipse:
   - Modificar las rutas en el archivo Java para que correspondan a tu sistema.
   - Ejecutar como una aplicación Java.

### 4. Ajustar Archivos para CatE
1. Limpiar los archivos de prueba y validación:
   ```bash
   python cleaned.py
   ```
2. Verificar consistencias entre los nodos de los archivos generados.

---

## Entrenamiento del Modelo

1. Realizar ajustes en los scripts de CatE:
   - En `cat.py`, agregar soporte para la ontología personalizada.
   - En `run_cat_completion.py`, incluir la ontología como caso de uso.

2. Ejecutar el script de entrenamiento desde la carpeta `use_cases`:
   ```bash
   python run_cat_completion.py --batch_size=8192 --emb_dim=200 --loss_type=normal --lr=0.0001 --margin=1 --num_negs=2 --use_case=ontologia -ns
   ```

---

## Problemas Comunes y Soluciones

1. **Error con nodos inconsistentes:**
   - Verificar y eliminar nodos adicionales en los archivos generados.

2. **Problemas con Java y JVM:**
   - Asegurarse de que `JAVA_HOME` esté correctamente configurado.
   - Especificar la ruta completa del archivo `jvm.dll` en el script.

3. **Dependencias faltantes:**
   - Instalar manualmente cualquier dependencia que no se haya configurado automáticamente.

---

## Próximos Pasos

Aunque no fue posible completar todo el entrenamiento, los pasos realizados hasta ahora dejan una base sólida para continuar con el trabajo. Queda pendiente resolver el problema relacionado con el tamaño de los tensores durante el entrenamiento y explorar más a fondo las posibilidades de CatE en combinación con ontologías personalizadas.
