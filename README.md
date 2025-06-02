# 🤖 Sistema de Automação de Currículos para RH

Sistema automatizado em Python que processa e-mails de candidatura, extrai informações dos candidatos e organiza currículos automaticamente.

## 📋 Funcionalidades

- ✅ Processamento automático de e-mails via IMAP Gmail
- ✅ Extração de dados usando regex (nome, telefone, vaga)
- ✅ Organização automática de currículos
- ✅ Planilha Excel com histórico de candidatos
- ✅ Sistema de logs detalhado

## 🛠️ Por que Python?

Python foi escolhido por suas bibliotecas nativas para e-mail (imaplib) e manipulação de dados (pandas), facilidade de manutenção e ecossistema robusto. Oferece melhor custo-benefício comparado a soluções RPA comerciais.

## 📁 Estrutura Gerada

```
automacao_curriculos/
├── curriculos/          # Arquivos CV organizados
├── logs/               # Logs de execução
└── candidatos.xlsx     # Planilha com dados
```

## 🚀 Instalação e Uso

### Dependências
```bash
pip install pandas openpyxl chardet
```

### Configuração Gmail
1. Ative autenticação de 2 fatores
2. Gere senha de aplicativo
3. Configure no código:
   ```python
   EMAIL_USER = "seu-email@gmail.com"
   EMAIL_PASS = "sua-senha-de-aplicativo"
   ```

### Executar
```bash
python main.py
```

## 🔧 Principais Desafios Superados

- **Integração Gmail**: Configuração IMAP SSL e autenticação
- **Encoding variável**: Detecção automática de diferentes codificações
- **Extração de dados**: Regex flexíveis para formatos variados de e-mail
- **Alternativa RPA**: UiPath descartado por dificuldades de integração e custo

## 🔒 Confiabilidade

- Sistema de logs com níveis DEBUG, INFO, ERROR
- Validação de dados obrigatórios
- Controle de duplicação na planilha Excel
- Marcação automática de e-mails processados

## 🚀 Melhorias Futuras

- Interface web para estatísticas
- Configuração externa via arquivo
- Validação automática de currículos
- **Deploy AWS Lambda** com execução serverless e escalabilidade automática
