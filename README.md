# Saudações WhatsApp

Interface local para selecionar contatos e preparar o envio de saudações pelo WhatsApp Web.

## Executar

Requer Python 3.10 ou superior. Instale as dependências e inicie o servidor:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:8765 no navegador. Entre no WhatsApp Web antes do envio e mantenha o navegador padrão disponível. Para encerrar, pressione `Ctrl+C` no terminal.

## Banco de contatos

Por padrão, o aplicativo usa SQLite e cria `data/contacts.sqlite3` na primeira execução. Na primeira inicialização de um banco vazio, os contatos ativos de `contato.py` são importados uma única vez. Linhas comentadas não eram contatos ativos e não são importadas. Depois da migração, a interface passa a usar o banco; excluir todos os contatos não dispara uma nova importação.

Na tela de contatos, use **Novo contato**, **Editar** e **Excluir** para manter a agenda. Telefones devem estar no formato internacional, por exemplo `+5516999999999`. A exclusão pede confirmação. Não é possível alterar a agenda enquanto um envio está em andamento.

O arquivo SQLite contém dados pessoais e fica fora do Git pelo `.gitignore`.

### Usar PostgreSQL

Defina `DATABASE_URL` antes de iniciar o aplicativo. Exemplo no PowerShell:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO"
python app.py
```

No macOS/Linux:

```bash
export DATABASE_URL="postgresql+psycopg://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO"
python app.py
```

O banco e o usuário PostgreSQL devem existir e ter permissão para criar tabelas. As tabelas são criadas na inicialização; em um banco inicialmente vazio, os contatos ativos de `contato.py` também serão importados uma vez. **Mantenha `DATABASE_URL` em uma variável de ambiente e nunca publique a senha no repositório.**

## Envio

Selecione os contatos desejados, revise a mensagem e os intervalos e confirme o início. Os campos `{nome}` e `{saudacao}` são substituídos para cada destinatário. Envie somente para contatos que autorizaram o recebimento.

O navegador é controlado por automação de teclado durante o envio; evite utilizá-lo até o processo terminar.
