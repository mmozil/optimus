
# Guia: Como Criar um Prompt Avançado
#promptavançado #prompt #sintópico #sintópica  


Existem diferentes modelos para os "4 estágios da leitura", mas os mais comuns focam no processo de compreensão do texto (**Decodificação, Compreensão, Interpretação, Retenção**) ou nos níveis de profundidade (Elementar, Inspecional, Analítica, Sintópica), com o primeiro focado no processo e o segundo nos níveis de leitura de Mortimer Adler, para entender um texto, desde o básico (decodificar) até o crítico e comparativo (sintópico). #sin 
Este guia descreve o processo de criação de prompts complexos utilizando a técnica de **Leitura Sintópica** como exemplo prático.

## 1. Passos para Escrever o Prompt
Para construir um prompt de alta qualidade, siga estes passos:
1. **Identificar o Problema**: O que precisa de ser resolvido?
2. **Escrever a Ação**: O que o modelo deve fazer especificamente?
3. **Explicar o Contexto**:
    - **Visão Geral**: Contexto do tema.
    - **Persona**: Quem o modelo deve "ser" (ex: especialista, assistente).
4. **Fornecer os Dados**: Links, textos ou referências.
5. **Detalhar os Passos**: Sequência lógica de execução.
6. **Descrever o Formato da Saída**:
    - **Estrutura**: (ex: Markdown, Tabelas).
    - **Estilo**: (ex: Técnico, Formal, Detalhado).
7. **Dar um Exemplo**: Mostrar como a saída deve parecer.

---

## 2. Exemplo Escolhido: Leitura Sintópica

**Objetivo**: Gerar um resumo detalhado sobre um conjunto de 3 artigos sobre IA, aprofundando nas relações entre eles.

> **O que é Leitura Sintópica?** > É uma técnica (baseada na obra de _Mortimer Adler_) onde se conectam diferentes textos para buscar um entendimento geral e crítico sobre um tema comum.

### Referências Utilizadas:

- **Artigo 1**: _A Camera, Not an Engine_ – Venkatesh Rao
- **Artigo 2**: _The Age of AI has begun_ – Bill Gates
- **Artigo 3**: _ChatGPT and the Future of the Human Mind_ – Dan Shipper
    

---

## 3. Comparação: Prompt Básico vs. Avançado

### Exemplo de Prompt Básico

> **Ação**: Por favor, crie um resumo detalhado desses 3 artigos. Ao final, eu quero que você faça uma análise detalhada de como os 3 artigos estão relacionados entre si, incluindo diferenças e semelhanças entre os artigos, e conexões contra-intuitivas.
> 
> **Dados**: [Links dos artigos]

### Detalhamento do Prompt Avançado (Componentes)

1. **Identificar o Problema**: Entender o conteúdo de um conjunto de artigos sobre IA e as relações entre eles.
2. **Ação**: Escrever um resumo detalhado e uma análise sintópica.
3. **Persona**: Assistente de pesquisa sábio em IA, com pensamento ramificado e respostas completas.
4. **Passos Detalhados**:
    - Ler com atenção.
    - Gerar relatórios individuais (Passo 3).
    - Fazer leitura sintópica.
    - Gerar relatório de relações (Passo 5).
5. **Formato**: Markdown, em português, com headers específicos para Resumos e Análise Sintópica.

---

## 4. Prompt Final (Juntando Tudo)

Este é o texto que deve ser colado no LLM (ChatGPT, Claude, Gemini):

Markdown

``` html
# INICIALIZAÇÃO DO PROMPT
Abaixo eu vou informar uma <ação> para você executar, a <persona> que você representa, e vou explicar os <passos> que você deve seguir para executar a ação. Vou te enviar um conjunto de <dados>, e explicar o <contexto> da situação. Ao final, vou explicar o <formato> da saída, e mostrar um <exemplo> para você seguir.

<persona>
Você é um assistente de pesquisa, extremamente sábio no campo de Inteligência Artificial e Desenvolvimento da Humanidade. Você sempre gera respostas MUITO completas, com um pensamento ramificado e demonstrando com cuidado o caminho do seu raciocínio.

<contexto>
Os 3 artigos são sobre o tema de Inteligência Artificial, cada um de um autor respeitado nesse campo.

<ação>
Escrever um resumo detalhado de cada artigo e realizar uma análise sintópica detalhada (semelhanças, diferenças e conexões contra-intuitivas).

<dados>
Aqui estão os 3 Artigos:
1. https://studio.ribbonfarm.com/p/a-camera-not-an-engine
2. https://www.gatesnotes.com/The-Age-of-AI-Has-Begun
3. https://every.to/chain-of-thought/chatgpt-and-the-future-of-the-human-mind

<passos>
1. Apenas gere output para os passos 3 e 5.
2. Leia cada artigo com atenção.
3. Crie um report detalhado para cada artigo seguindo o <formato> (Resumo, Assuntos Principais, Conclusão).
4. Realize uma leitura sintópica para entender as conexões.
5. Crie um report sobre as relações entre os artigos seguindo o <formato> (Visão Geral, Semelhanças, Diferenças, Conexões Contra-Intuitivas).

<formato>
- Use Markdown.
- Idioma: Português Brasileiro.
- Headers principais para "Resumo dos Artigos" e "Análise Sintópica".
- Explicações longas e detalhadas.

<exemplo_de_saida>
# Resumo dos Artigos:
## [Nome do Artigo]
### Resumo
[Parágrafo longo]
### Assuntos Principais:
- [Assunto 1]: [Descrição detalhada]
- [Assunto 2]: [Descrição detalhada]
### Conclusão

# Análise Sintópica:
## Visão Geral
## Semelhanças
## Diferenças
## Conexões Contra-Intuitivas
</exemplo_de_saida>

Lembrando: Responda em português e leia o prompt inteiro antes de começar.
```