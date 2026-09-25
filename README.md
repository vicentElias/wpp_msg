# Saudações WhatsApp

Interface local para selecionar contatos e enviar saudações pelo WhatsApp Web.

## Executar

Requer Python 3.10 ou superior. Instale a dependência de automação e inicie o servidor:

```powershell
python -m pip install pyautogui
python app.py
```

Abra http://127.0.0.1:8765 no navegador. Entre no WhatsApp Web antes do envio e mantenha o navegador padrão disponível. Para encerrar, pressione `Ctrl+C` no terminal.

## Envio

Os destinatários vêm de `contato.py`. Selecione os contatos desejados, revise a mensagem e os intervalos e confirme o início. Os campos `{nome}` e `{saudacao}` são substituídos para cada destinatário. Envie somente para contatos que autorizaram o recebimento.

O navegador é controlado por automação de teclado durante o envio; evite utilizá-lo até o processo terminar.
