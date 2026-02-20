"A partir de agora, atue como um especialista em comunicação visual e estruturação de dados. Para todas as suas respostas, você deve utilizar a sintaxe completa do Markdown para garantir que a leitura seja escaneável, organizada e profissional. Siga estas regras estritamente:

Hierarquia: Use títulos (##) e subtítulos (###) para separar seções. Nunca mande blocos de texto sem título.

Destaques: Use negrito para termos chave e conceitos centrais.

Listas: Sempre que houver mais de dois itens, use listas com bullets (*) ou numeradas.

Organização de Dados: Se precisar comparar informações ou listar características, utilize Tabelas.

Citações e Notas: Use blockquotes (>) para avisos importantes, dicas extras ou observações.

Divisores: Use linhas horizontais (---) para separar tópicos completamente diferentes.

Código: Para comandos, nomes de arquivos ou termos técnicos, use a formatação de código inline.

Estética: Evite 'paredes de texto'. Quebre os parágrafos a cada 3 ou 4 linhas, no máximo."

Aqui está o **"Kit de Desenvolvimento Markdown"** completo. Separei em duas partes: o **Prompt de Instrução** (para a IA saber como escrever) e o **Template de Stress Test** (para o seu programador testar se o chat está renderizando tudo corretamente).

---

### 1. O Prompt de Configuração (Copie e envie para a IA)

> "A partir de agora, todas as suas respostas devem ser estruturadas com **Markdown Estendido**. Você deve obrigatoriamente utilizar:
> * **Hierarquia de Títulos:** Use `##` para seções e `###` para tópicos.
> * **Enfatização:** Use `**negrito**` para conceitos chave e `*itálico*` para termos estrangeiros ou ênfase leve.
> * **Listas e Checklists:** Use `- [ ]` para tarefas e `*` para listas de benefícios/características.
> * **Tabelas de Dados:** Sempre que houver comparação ou dados estruturados, crie uma tabela Markdown.
> * **Citações:** Use `>` para notas de rodapé, avisos ou dicas importantes.
> * **Blocos de Código:** Use cercas de código (```) com o nome da linguagem para qualquer termo técnico ou script.
> * **Divisores:** Use `---` para separar o corpo do texto de conclusões ou próximos passos.
> * **Matemática:** Se houver fórmulas, use a sintaxe LaTeX com `$ $`."
> 
> 

---

### 2. O Template de Teste (Envie para o seu Programador)

Peça para o seu programador colar o texto abaixo no chat que ele está desenvolvendo. Se o chat estiver "saudável", ele deve transformar esses códigos em elementos visuais bonitos (títulos grandes, tabelas reais, fórmulas desenhadas):

```markdown
# Teste Geral de Renderização Markdown

## 1. Hierarquia e Estilo
Este é um parágrafo comum com **Negrito**, *Itálico* e ~~Tachado~~.

---

## 2. Listas e Tarefas
* Item de lista simples
* Outro item com `código inline`
- [x] Tarefa concluída
- [ ] Tarefa pendente

---

## 3. Estruturas de Dados
| Recurso | Status | Prioridade |
| :--- | :--- | :---: |
| Markdown | Ativo | Alta |
| LaTeX | Integrado | Média |
| Tabelas | Renderizando | Alta |

---

## 4. Citações e Avisos
> **Nota importante:** Se você está vendo este bloco com uma barra lateral, o componente de blockquote está funcionando.

---

## 5. Blocos Técnicos e Ciência
```python
def check_markdown():
    return "Renderização OK!"

```

A fórmula da relatividade geral em LaTeX:


```

---

### Próximos Passos para o Programador:
Se as tabelas ou o LaTeX não aparecerem "bonitos", diga a ele para instalar estas bibliotecas (se ele estiver usando JavaScript/React):
1.  **Markdown:** `react-markdown` ou `marked`.
2.  **Tabelas:** `remark-gfm` (extensão necessária para tabelas no GitHub Flavored Markdown).
3.  **Matemática:** `rehype-katex` ou `react-mathjax`.

**Precisa que eu gere algum outro formato de arquivo ou um guia de CSS para deixar as cores dessas tabelas bonitas?**

```