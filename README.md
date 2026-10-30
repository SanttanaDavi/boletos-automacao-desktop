# Organização de boletos em PDF

Exemplo de pesquisa por título, espera de download e organização de PDFs.

**Estado: código educacional/legado para consulta, sem licença de reutilização concedida. Sem validação funcional nesta preparação.**

## Autoria

Desenvolvido por **David Santana** — [@SanttanaDavi](https://github.com/SanttanaDavi).

Esta é uma adaptação pública para estudo, com configurações locais removidas e entrada protegida. Não distribui dados ou configurações de qualquer organização.

## Começar sem executar automações

1. Leia este documento, PRIVACIDADE.md e LIMITACOES.md.
2. Revise os arquivos e providencie seu próprio ambiente Python. Nada é instalado pelo projeto.
3. A entrada **python automacao.py** só mostra instruções. Não importa o adaptador nem abre navegador, planilha ou conexão SMTP.
4. **.env.example** documenta as variáveis; ele não é carregado automaticamente. Nunca grave credenciais nesse exemplo nem envie configurações pessoais ao GitHub.
5. Somente depois de adaptar os seletores e revisar o fluxo com dados fictícios, **python automacao.py --executar** carrega o legado. Além da opção, exige **AUTOMACAO_CONFIRMAR_EXECUCAO=EU_REVISEI** no processo. Isso não substitui autorização para operar um sistema.

**adaptador_legado.py** conserva a estrutura do script de origem, com saneamento e configuração externa; também bloqueia execução direta/importação por padrão. **configuracao.py** centraliza parâmetros e travas da edição pública.

## Configuração e dependências

As dependências diretas estão em requirements.txt. As versões não foram homologadas nesta preparação; não há promessa de build reproduzível. Tkinter/Tcl-Tk e bibliotecas de automação precisam funcionar no ambiente escolhido. Não são incluídos Python, navegador, drivers, instaladores ou binários.

Quando houver Selenium, forneça o caminho de um driver já instalado e compatível. A edição não deve depender de download automático de driver. Configure seu próprio endereço HTTPS; nenhum endereço institucional acompanha a cópia.

Os legados que usam planilhas em geral esperam XLSX. **exemplo.csv**, se presente, é somente referência de colunas com conteúdo fictício, separado por ponto e vírgula. Não é uma planilha operacional pronta; precisa ser convertida e complementada conforme o adaptador.

## Conferência realizada

- Retirada de credenciais literais, identificadores locais, contatos e referências da instalação original.
- Configuração externa de caminhos e alvos; bloqueio de execução por padrão.
- Preparação por leitura e edição de fontes. **Não foram executados scripts, testes de sintaxe ou testes funcionais nesta preparação.**

O utilitário **verificar_copia.py** analisa o texto dos três módulos locais com a biblioteca padrão, sem importar o adaptador, ler planilhas ou usar rede. Sua presença não significa que já foi executado; sua análise não certifica ausência de todo segredo possível.

## Contribuir

Veja CONTRIBUTING.md. Use somente casos fictícios e erros saneados, sem planilhas preenchidas, capturas reais, dados pessoais, credenciais, documentos financeiros ou logs operacionais.

## Direitos e forma de publicação

Copyright (c) 2026 David Santana. Todos os direitos reservados.

O código está público para consulta e portfólio. Nenhuma licença MIT ou outra licença de reutilização foi concedida. Para usar, modificar ou redistribuir além das permissões dos termos do GitHub e das exceções legais aplicáveis, solicite autorização ao autor. Veja DIREITOS.md.
