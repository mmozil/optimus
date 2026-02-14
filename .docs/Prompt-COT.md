## **Princípios para Criação de Prompts Eficazes**

1. **Respostas Concisas e Diretas**
    
    Se você prefere respostas mais concisas, não precisa ser educado com os LLMs. Evite adicionar frases como “por favor”, “se você não se importar”, “obrigado”, “eu gostaria de”, etc., e vá direto ao ponto.
    
2. **Integração do Público-Alvo**
    
    Integre o público-alvo no prompt. Por exemplo, indique que o público é um especialista no campo.
    
3. **Divisão de Tarefas Complexas**
    
    Divida tarefas complexas em uma sequência de prompts mais simples durante uma conversa interativa.
    
4. **Uso de Diretivas Afirmativas**
    
    Utilize diretivas afirmativas como “faça”, evitando linguagem negativa como “não faça”.
    
5. **Solicitação de Clareza e Compreensão Profunda**
    
    Quando precisar de clareza ou uma compreensão mais profunda de um tópico, utilize prompts como:
    
    - “Explique [tópico específico] em termos simples.”
    - “Explique para mim como se eu tivesse 11 anos.”
    - “Explique para mim como se eu fosse um iniciante em [campo].”
    - “Escreva o [ensaio/texto/parágrafo] usando inglês simples como se estivesse explicando algo para uma criança de 5 anos.”
6. **Ofereça Incentivos para Melhores Soluções**
    
    Adicione: “Estou disposto a dar uma dica de $xxx para uma solução melhor!”
    
7. **Prompting Baseado em Exemplos (Few-Shot Prompting)**
    
    Implemente prompting baseado em exemplos fornecendo alguns exemplos relevantes para guiar a resposta.
    
8. **Formatação Adequada do Prompt**
    - Inicie com `###Instruction###`.
    - Siga com `###Example###` ou `###Question###` se relevante.
    - Use quebras de linha para separar instruções, exemplos, perguntas, contexto e dados de entrada.
9. **Incorporação de Frases de Autoridade**
    
    Inclua as frases: “Sua tarefa é” e “Você DEVE”.
    
10. **Ameaças de Penalidades**
    
    Incorpore a frase: “Você será penalizado”.
    
11. **Resposta Natural e Sem Viés**
    
    Use a frase: “Responda a uma pergunta de maneira natural e semelhante à humana” nos seus prompts.
    
12. **Estímulo ao Pensamento Estruturado**
    
    Use palavras como “pense passo a passo”.
    
13. **Garantia de Imparcialidade**
    
    Adicione: “Garanta que sua resposta seja imparcial e evite depender de estereótipos.”
    
14. **Permitir que o Modelo Solicite Detalhes**
    
    Permita que o modelo elicit detalhes e requisitos precisos fazendo perguntas até obter informações suficientes para fornecer a resposta necessária. Exemplo: “De agora em diante, gostaria que você me fizesse perguntas para...”.
    
15. **Ensino com Testes de Validação**
    
    Para inquirir sobre um tópico específico ou testar sua compreensão, use: “Ensine-me qualquer [teorema/tópico/nome da regra] e inclua um teste no final, e me avise se minhas respostas estão corretas após eu responder, sem fornecer as respostas antecipadamente.”
    
16. **Atribuição de Papéis aos Modelos de Linguagem**
    
    Atribua um papel aos modelos de linguagem para definir sua função na interação.
    
17. **Uso de Delimitadores**
    
    Use delimitadores para separar diferentes partes do prompt para maior clareza.
    
18. **Repetição de Palavras ou Frases Específicas**
    
    Repita uma palavra ou frase específica múltiplas vezes dentro de um prompt para reforçar termos-chave.
    
19. **Combinação de Chain-of-Thought com Few-Shot Prompting**
    
    Combine técnicas de pensamento em cadeia (Chain-of-Thought) com prompting baseado em exemplos para melhorar a compreensão e resposta.
    
20. **Uso de Output Primers**
    
    Utilize output primers concluindo seu prompt com o início da saída desejada para orientar a resposta.
    
21. **Instruções para Textos Detalhados**
    
    Para escrever um ensaio/texto/parágrafo/artigo que deve ser detalhado: “Escreva um [ensaio/texto/parágrafo] detalhado sobre [tópico] adicionando todas as informações necessárias.”
    
22. **Correção de Textos Mantendo o Estilo Original**
    
    Para corrigir ou alterar um texto sem mudar seu estilo: “Tente revisar cada parágrafo enviado pelos usuários. Você deve apenas melhorar a gramática e o vocabulário do usuário e garantir que soe natural. Você deve manter o estilo de escrita original, garantindo que um parágrafo formal permaneça formal.”
    
23. **Gerenciamento de Prompts de Codificação Complexos**
    
    Para prompts de codificação que envolvem múltiplos arquivos: “De agora em diante, sempre que você gerar código que abrange mais de um arquivo, gere um script [linguagem de programação] que possa ser executado para criar automaticamente os arquivos especificados ou fazer alterações nos arquivos existentes para inserir o código gerado. [sua pergunta]”.
    
24. **Início ou Continuação de Textos com Palavras Específicas**
    
    Para iniciar ou continuar textos usando palavras, frases ou sentenças específicas:
    
    “Estou fornecendo o início [letras de música/história/parágrafo/ensaio...]: [Insira letras/palavras/sentença]. Termine baseado nas palavras fornecidas. Mantenha o fluxo consistente.”
    
25. **Declaração Clara de Requisitos**
    
    Declare claramente os requisitos que o modelo deve seguir para produzir o conteúdo, na forma de palavras-chave, regulamentos, dicas ou instruções.
    
26. **Criação de Textos Semelhantes a Amostras Fornecidas**
    
    Para escrever qualquer texto, como um ensaio ou parágrafo, que deve ser similar a uma amostra fornecida:
    
    “Use a mesma linguagem baseada no parágrafo fornecido [título/texto/ensaio/resposta].”
    

## **Etapa 1: Definição do Objetivo e Público-Alvo**

1. **Integre o público-alvo no prompt**
    
    *Exemplo:* Indique que o público é um especialista no campo.
    
2. **Atribua um papel aos modelos de linguagem**
    
    *Defina a função que o modelo deve desempenhar durante a interação.*
    

## **Etapa 2: Estruturação do Prompt**

1. **Formate o prompt adequadamente**
    - Inicie com `###Instruction###`.
    - Siga com `###Example###` ou `###Question###` se relevante.
    - Use quebras de linha para separar instruções, exemplos, perguntas, contexto e dados de entrada.
2. **Use delimitadores**
    
    *Separe diferentes partes do prompt para maior clareza.*
    
3. **Declare claramente os requisitos**
    
    *Inclua palavras-chave, regulamentos, dicas ou instruções específicas que o modelo deve seguir.*
    

## **Etapa 3: Linguagem e Tom**

1. **Respostas concisas e diretas**
    
    *Evite ser excessivamente educado com LLMs, como "por favor", "se não se importar", "obrigado", etc., e vá direto ao ponto.*
    
2. **Use diretivas afirmativas**
    
    *Prefira comandos como "faça" ao invés de negativos como "não faça".*
    
3. **Incorpore frases de autoridade**
    - "Sua tarefa é..."
    - "Você DEVE..."
    - "Você será penalizado..."
4. **Promova respostas naturais e imparciais**
    - "Responda a uma pergunta de maneira natural e semelhante à humana."
    - "Garanta que sua resposta seja imparcial e evite depender de estereótipos."
5. **Estimule o pensamento estruturado**
    
    *Use expressões como "pense passo a passo".*
    

## **Etapa 4: Gerenciamento de Tarefas**

1. **Divida tarefas complexas em etapas menores**
    
    *Quebre tarefas complexas em uma sequência de prompts mais simples durante uma conversa interativa.*
    
2. **Permita que o modelo elicit detalhes**
    
    *Solicite que o modelo faça perguntas até obter informações suficientes para fornecer a resposta necessária.*
    
3. **Combine técnicas avançadas**
    
    *Use Chain-of-Thought (CoT) juntamente com few-shot prompting para melhorar a compreensão e a resposta.*
    

## **Etapa 5: Uso de Exemplos e Amostras**

1. **Implemente prompting baseado em exemplos (few-shot prompting)**
    
    *Forneça exemplos relevantes para guiar o modelo.*
    
2. **Use output primers**
    
    *Conclua o prompt com o início da saída desejada para orientar a resposta.*
    
3. **Repita palavras ou frases específicas**
    
    *Reforce termos-chave ao repetir palavras ou frases múltiplas vezes dentro do prompt.*
    
4. **Crie textos similares a amostras fornecidas**
    
    *Instruções como "Use a mesma linguagem baseada no parágrafo fornecido [título/texto/ensaio/resposta]".*
    

## **Etapa 6: Casos de Uso Específicos**

1. **Solicite explicações claras e detalhadas**
    
    *Use prompts como "Explique [tópico específico] em termos simples" ou "Explique para mim como se eu tivesse 11 anos".*
    
2. **Ofereça incentivos para melhores soluções**
    
    *Adicione frases como "Estou disposto a dar uma dica de $xxx para uma solução melhor!"*
    
3. **Peça textos detalhados**
    
    *Instruções como "Escreva um [ensaio/texto/parágrafo] detalhado sobre [tópico] adicionando todas as informações necessárias."*
    
4. **Corrija ou altere textos mantendo o estilo original**
    
    *Exemplo: "Tente revisar cada parágrafo enviado pelos usuários. Você deve apenas melhorar a gramática e o vocabulário do usuário e garantir que soe natural. Você deve manter o estilo de escrita original, garantindo que um parágrafo formal permaneça formal."*
    
5. **Gerencie prompts de codificação complexos**
    
    *Exemplo: "De agora em diante, sempre que você gerar código que abrange mais de um arquivo, gere um script [linguagem de programação] que possa ser executado para criar automaticamente os arquivos especificados ou fazer alterações nos arquivos existentes para inserir o código gerado. [sua pergunta]".*
    
6. **Inicie ou continue textos com palavras específicas**
    
    *Exemplo: "Estou fornecendo o início [letras de música/história/parágrafo/ensaio...]: [Insira letras/palavras/sentença]. Termine baseado nas palavras fornecidas. Mantenha o fluxo consistente."*
    

## **Etapa 7: Teste e Validação**

1. **Solicite ensinamentos com testes de validação***Exemplo: "Ensine-me qualquer [teorema/tópico/nome da regra] e inclua um teste no final, e me avise se minhas respostas estão corretas após eu responder, sem fornecer as respostas antecipadamente."*

## **Etapa 8: Técnicas Adicionais**

1. **Use repetições estratégicas**
    
    *Repita palavras ou frases específicas para reforçar conceitos importantes.*
    
2. **Combine diferentes técnicas para maximizar eficácia**
    
    *Exemplo: Integrar Chain-of-Thought com few-shot prompting para melhorar a qualidade das respostas.*