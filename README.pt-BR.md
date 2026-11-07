<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/media/wordmark-dark.png">
  <img src="docs/media/wordmark-light.png" alt="Invenux" height="84">
</picture>

<br>
<br>

**Inventário de hardware Linux via SSH, a partir de uma planilha de máquinas.**

Sem agente e só leitura: nada é instalado ou gravado nas máquinas.

<br>

<a href="https://github.com/lucaswotta/invenux/stargazers"><img src="https://img.shields.io/github/stars/lucaswotta/invenux?style=flat-square&logo=github&labelColor=1C1C1E&color=0A84FF" alt="Estrelas no GitHub"></a>
<a href="https://github.com/lucaswotta/invenux/releases/latest"><img src="https://img.shields.io/github/v/release/lucaswotta/invenux?style=flat-square&labelColor=1C1C1E&color=0A84FF" alt="Última versão"></a>
<a href="https://github.com/lucaswotta/invenux/actions/workflows/quality.yml"><img src="https://img.shields.io/github/actions/workflow/status/lucaswotta/invenux/quality.yml?branch=main&style=flat-square&label=CI&labelColor=1C1C1E&color=0A84FF" alt="CI"></a>
<a href="https://github.com/lucaswotta/invenux/commits/main"><img src="https://img.shields.io/github/last-commit/lucaswotta/invenux?style=flat-square&labelColor=1C1C1E&color=0A84FF" alt="Último commit"></a>
<a href="LICENSE"><img src="https://img.shields.io/github/license/lucaswotta/invenux?style=flat-square&labelColor=1C1C1E&color=0A84FF" alt="Licença MIT"></a>
<img src="https://img.shields.io/badge/python-3.11%2B-0A84FF?style=flat-square&labelColor=1C1C1E&logo=python&logoColor=white" alt="Python 3.11+">
<img src="https://img.shields.io/badge/roda%20em-Linux%20%C2%B7%20Windows%20%C2%B7%20macOS-0A84FF?style=flat-square&labelColor=1C1C1E" alt="Roda em Linux, Windows e macOS">
<img src="https://img.shields.io/badge/interface-PT--BR%20%C2%B7%20EN%20%C2%B7%20ES-0A84FF?style=flat-square&labelColor=1C1C1E" alt="Interface em português, inglês e espanhol">
<img src="https://img.shields.io/badge/telemetria-nenhuma-0A84FF?style=flat-square&labelColor=1C1C1E" alt="Sem telemetria">
<a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-bem--vindos-0A84FF?style=flat-square&labelColor=1C1C1E" alt="Pull requests bem-vindos"></a>

<br>

[Baixar](https://github.com/lucaswotta/invenux/releases/latest) ·
[Recursos](#recursos) ·
[Instalação](#instalação) ·
[Como usar](#como-usar) ·
[A planilha](#a-planilha) ·
[Perguntas](#perguntas-frequentes) ·
[Contribuir](CONTRIBUTING.md) ·
[English](README.md) ·
[Español](README.es.md)

<br>

<img src="docs/media/demo-pt-br.gif" width="900" alt="Carregando uma planilha de 24 máquinas, informando o acesso SSH, coletando, abrindo os detalhes de uma máquina, a visão Parque e a exportação para Excel">

</div>

## Por que o Invenux

- **Entra uma planilha, sai um inventário.** Liste as máquinas com o IP, informe o acesso SSH e inicie. Cada máquina aparece com processador, slots de memória, discos, placa-mãe, BIOS, vídeo, rede e sistema operacional.
- **Nada para instalar nas máquinas.** Uma conexão SSH executa um único script de leitura por máquina. Sem agente, sem serviço e sem arquivo gravado no destino.
- **Diz por que uma máquina falhou.** Desligada, porta SSH fechada, tempo esgotado, nome inexistente, senha errada ou chave do host trocada, cada caso com sua mensagem.
- **Relatórios que as pessoas abrem.** Excel com aba de resumo e colunas agrupadas, página HTML pesquisável que funciona offline, e CSV.
- **Histórico sem servidor de banco.** Cada coleta fica salva no computador e é comparada campo a campo com a anterior, então um disco trocado ou uma memória a mais aparece na hora.

## Recursos

| Área | O que você tem |
| --- | --- |
| **Coleta** | Até 128 conexões SSH em paralelo em qualquer porta SSH (22 por padrão), senha ou chave privada, confiança no primeiro acesso para chaves de host, cancelamento a qualquer momento. |
| **Sistema** | Distribuição, versão e codinome, kernel, arquitetura, hostname, ambiente gráfico e servidor de vídeo, telas, quantidade de pacotes, init, fuso horário, tempo ligado, uso do disco `/`. |
| **Hardware** | Fabricante e modelo, placa-mãe, BIOS, processador com núcleos, threads e frequência, cada slot de memória (tamanho, tipo, velocidade, modelo do pente) e o máximo da placa, cada disco e partição, vídeo, adaptadores de rede com IPv4 e MAC. |
| **Parque** | Tipos de armazenamento, capacidade de memória e distribuições Linux das máquinas acessíveis, e a divisão por local. |
| **Snapshots** | Histórico local de cada coleta com comparação campo a campo com o anterior ou com qualquer outro (**Comparar com**), exportável em CSV com as duas datas. Exclua um snapshot (com confirmação) ou defina a retenção em Sobre e ajustes (manter os últimos N, ou os dos últimos N dias; aplicada ao fim de cada coleta, o mais recente sempre fica). |
| **Exportação** | Excel (resumo com barras de proporção, inventário agrupado por assunto), HTML interativo que funciona offline, CSV com proteção contra fórmulas. |
| **Interface** | Português, inglês e espanhol, seguindo o idioma do sistema; guia embutido com tutorial animado; redimensionável até 720 × 520. |
| **Desktop** | Janela nativa no Linux, Windows e macOS (pywebview ou GTK), ou o navegador; pacotes prontos para os três sistemas; janela Sobre e ajustes (rodapé da barra lateral ou nome do app) com idioma, tema claro ou escuro, versão e atualização com um clique quando sai versão nova. |

<div align="center">

<img src="docs/media/hero-pt-br.png" width="900" alt="Visão Coleta: 24 máquinas com status, endereço, hostname, local, processador, memória, armazenamento e sistema, e os detalhes de uma máquina à direita">

</div>

<table>
  <tr>
    <td width="50%"><img src="docs/media/fleet-pt-br.png" alt="Visão Parque com armazenamento, memória, distribuições e a tabela por local"></td>
    <td width="50%"><img src="docs/media/excel-pt-br.png" alt="Aba de resumo do Excel com cartões de indicadores e tabelas com barras"></td>
  </tr>
  <tr>
    <td align="center">Visão Parque</td>
    <td align="center">Exportação para Excel</td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/media/onboarding-pt-br.png" alt="Primeiro uso: três passos e o tutorial animado mostrando como a planilha é lida"></td>
    <td width="50%"><img src="docs/media/help-pt-br.png" alt="Tela Como usar com o tutorial, o passo a passo, as pastas e as colunas da planilha"></td>
  </tr>
  <tr>
    <td align="center">Primeiro uso</td>
    <td align="center">Guia embutido</td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/media/light-pt-br.png" alt="Visão Parque no tema claro"></td>
    <td width="50%"><img src="docs/media/narrow-pt-br.png" alt="Visão Coleta numa janela de 760 px, com os detalhes abaixo da tabela"></td>
  </tr>
  <tr>
    <td align="center">Tema claro</td>
    <td align="center">Janela estreita</td>
  </tr>
</table>

## Instalação

### Baixar

Baixe o arquivo do seu sistema na [última versão](https://github.com/lucaswotta/invenux/releases/latest):

| Sistema | Arquivo | Como abrir |
| --- | --- | --- |
| Windows 10/11 (x86_64) | `invenux-<versão>-windows-x86_64.exe` | Execute. O SmartScreen avisa que o programa não é assinado: **Mais informações** e depois **Executar assim mesmo**. |
| macOS (Apple Silicon ou Intel) | `invenux-<versão>-macos-arm64.zip` ou `-macos-x86_64.zip` | Descompacte e abra o `Invenux.app`. Na primeira vez, clique com o botão direito e escolha **Abrir**, porque o app não é notarizado. |
| Linux (x86_64, glibc 2.35 ou mais recente) | `invenux-<versão>-linux-x86_64.tar.xz` | Extraia e rode `./install.sh` para colocar no menu de aplicativos, ou rode `./invenux` na pasta. |

Os pacotes não têm assinatura de código; o `SHA256SUMS` da versão lista os checksums. Cada um abre a própria janela: WebView2 no Windows (parte do Windows 10 e 11), WebKit no macOS e um Qt WebEngine embutido no Linux, por isso o download do Linux tem cerca de 135 MB.

### A partir do código

**Requisitos:** Python 3.11 ou mais recente e máquinas Linux acessíveis por SSH (porta 22 por padrão, configurável).

```sh
git clone https://github.com/lucaswotta/invenux.git
cd invenux
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python3 -m pip install -r requirements.txt
python3 app.py
```

A janela usa o [pywebview](https://pywebview.flowrl.com/) quando ele está instalado, depois o GTK WebKit2 no Linux (`python3-gi` e `gir1.2-webkit2-4.1` no Debian e Ubuntu, visíveis num venv criado com `--system-site-packages`) e, sem nenhum dos dois, abre a interface no navegador padrão. No navegador, o programa encerra cerca de 3 minutos depois que a aba é fechada.

**Pacote nativo.** `python build.py` gera o pacote do sistema em que roda (o PyInstaller não faz compilação cruzada): um `.exe` no Windows, uma pasta no Linux e um app no macOS. Uma tag `v*` faz o CI gerar os pacotes de Linux, Windows e macOS e publicá-los como release no GitHub.

```sh
python3 -m pip install -r requirements-build.txt
python3 build.py                   # dist/invenux-v0.9.2
```

No Linux, `./install.sh` na pasta extraída da release copia o programa para `~/.local/lib/invenux`, cria o link `~/.local/bin/invenux` e adiciona o atalho e o ícone no menu, sem sudo. `./install.sh --uninstall` remove tudo e mantém histórico e relatórios.

## Como usar

1. **Alvos:** escolha a planilha de máquinas, arraste o arquivo para a janela ou cole o caminho. Ainda não tem planilha? Use **Baixar planilha modelo**.
2. **SSH:** informe o usuário, a porta (22, a menos que suas máquinas usem outra) e uma senha ou chave privada. A senha fica só na memória.
3. **Iniciar coleta:** acompanhe cada máquina na tabela e clique numa linha para ver os detalhes.
4. **Exportar:** Excel, HTML ou CSV, salvos na pasta `Invenux` dentro de Documentos, com **Abrir** e **Abrir pasta** logo em seguida.

O botão `Como usar` tem o tutorial animado, o formato da planilha, o significado de cada status e botões para abrir as pastas de relatórios, histórico e logs.

**Linha de comando.** Coleta e exporta sem interface. Use `--key`, ou a senha pela variável de ambiente `INVENUX_SSH_PASSWORD` ou por `--ask-password` (pergunta sem mostrar o que é digitado); não existe opção de senha, para ela nunca aparecer na lista de processos nem no histórico do shell:

```sh
python3 app.py --input maquinas.xlsx --user inventario --key ~/.ssh/id_ed25519 --ssh-port 22 --output-format XLSX
python3 app.py --input maquinas.xlsx --user inventario --ask-password
```

### Coletas agendadas

`--report-changes ARQUIVO` faz uma coleta pela linha de comando gravar também as mudanças de hardware (processador, memória, armazenamento, placa-mãe) em relação ao snapshot anterior, das máquinas que estavam online nas duas coletas. Mudanças de status, sistema e kernel ficam de fora, e o arquivo fica vazio (0 bytes) quando nada mudou, para o agendador agir só quando houver conteúdo. Cada coleta grava um snapshot que aparece na visão Snapshots. Use chave, porque não há ninguém para digitar senha; os exemplos usam a instalação Linux (`~/.local/bin/invenux`), e `python3 /caminho/para/invenux/app.py` funciona igual a partir do código.

cron (toda segunda às 07:00, manda as mudanças por e-mail quando houver):

```sh
0 7 * * 1 $HOME/.local/bin/invenux --input $HOME/inventario/maquinas.xlsx --user inventario --key $HOME/.ssh/id_ed25519 --report-changes $HOME/inventario/mudancas.csv && [ -s $HOME/inventario/mudancas.csv ] && mail -s "Mudancas de hardware" admin@example.com < $HOME/inventario/mudancas.csv
```

Timer do systemd (`~/.config/systemd/user/invenux.service` e `invenux.timer`, depois `systemctl --user enable --now invenux.timer`):

```ini
# invenux.service
[Service]
Type=oneshot
ExecStart=%h/.local/bin/invenux --input %h/inventario/maquinas.xlsx --user inventario --key %h/.ssh/id_ed25519 --report-changes %h/inventario/mudancas.csv

# invenux.timer
[Timer]
OnCalendar=Mon 07:00
Persistent=true

[Install]
WantedBy=timers.target
```

Agendador de Tarefas do Windows (PowerShell, toda segunda às 07:00):

```powershell
$action = New-ScheduledTaskAction -Execute "C:\Ferramentas\invenux.exe" -Argument '--input C:\Inventario\maquinas.xlsx --user inventario --key C:\Users\eu\.ssh\id_ed25519 --report-changes C:\Inventario\mudancas.csv'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 7am
Register-ScheduledTask -TaskName "Inventario Invenux" -Action $action -Trigger $trigger
```

## A planilha

`.xlsx`, `.xlsm` ou `.csv` (vírgula ou ponto e vírgula). A primeira linha é o cabeçalho e cada linha seguinte é uma máquina.

| Coluna | Obrigatória | Uso |
| --- | --- | --- |
| `IP` | Sim | Endereço ou nome da máquina. Também vale `HOST`, `HOSTNAME`, `ADDRESS`, `IP_ADDRESS`, `ENDPOINT` ou `TARGET`. |
| `LOCATION` | Não | Unidade ou sala; agrupa o Parque e os relatórios. Também vale `LOCAL`, `UNIDADE`, `FILIAL`, `SETOR`, `SITE`, `UBICACION`, `SEDE` ou `SUCURSAL`. |
| `USER` | Não | Usuário SSH daquela máquina, quando difere do painel SSH. Também vale `USERNAME`, `SSH_USER`, `LOGIN` ou `USUARIO`. |
| `PASSWORD` | Não | Senha SSH daquela máquina, para parques com senhas diferentes; o normal é deixar a senha no painel SSH. Também vale `PASS`, `SENHA` ou `CONTRASENA`. Células vazias usam o painel. O Invenux a mantém só na memória e nunca a grava na tabela, relatórios, snapshots ou logs, mas o arquivo a guarda em texto puro. |
| `SSH_PORT` | Não | Porta SSH daquela máquina, quando não é a do painel. Também vale `PORT`, `PORTA` ou `PUERTO`. Células vazias usam o painel; linhas com porta inválida (fora de 1 a 65535) são ignoradas e listadas depois de carregar. A porta usada aparece nos detalhes e vai para os relatórios. |
| Qualquer outra | Não | Copiada como está para a tabela e para todos os relatórios, por exemplo `ASSET_TAG`, `OWNER` ou `NOTES`. |

Linhas sem IP e IPs repetidos são ignorados e listados depois de carregar. A planilha modelo (**Baixar planilha modelo**) vem com duas linhas de exemplo e uma aba explicando cada coluna, no idioma da interface.

## O que é coletado

Uma conexão SSH por máquina executa um único script de shell POSIX que lê:

| Fonte | Campos |
| --- | --- |
| `/etc/os-release`, `uname`, `/proc/1/comm`, `ps` | Distribuição, versão, kernel, arquitetura, hostname, init, ambiente gráfico e servidor de vídeo |
| `lscpu`, `/proc/cpuinfo` | Modelo do processador, soquetes, núcleos, threads, frequência máxima, extensão de virtualização |
| `/proc/meminfo`, `dmidecode -t memory` | Memória total, em uso e disponível; cada slot com tamanho, tipo, velocidade e modelo do pente |
| `lsblk`, `df` | Cada disco e partição, tipo (NVMe, SSD ou HDD), capacidade, uso do `/` |
| `/sys/class/dmi/id` | Fabricante, modelo, placa-mãe, BIOS |
| `lspci`, `/sys/class/drm` | Placas de vídeo e telas conectadas |
| `/sys/class/net`, `ip` | Adaptadores de rede, velocidade, driver, IPv4, MAC |
| `dpkg`, `rpm`, `pacman`, `apk`, `/etc/timezone` | Pacotes instalados, fuso horário |

Os slots de memória exigem root (`dmidecode`). Um usuário que não é root os obtém quando o sudo o deixa rodar o `dmidecode` sem senha (por exemplo `inventario ALL=(root) NOPASSWD: /usr/sbin/dmidecode` em `/etc/sudoers.d/`): a sonda então roda `sudo -n dmidecode -t memory`, que nunca pede senha e falha na hora sem essa regra. Sem nenhum dos dois, esses campos aparecem como indisponíveis e o resto é coletado normalmente. `Fontes utilizadas na coleta` nos relatórios diz se os slots vieram do `dmidecode`, do `sudo -n dmidecode` ou ficaram indisponíveis. Essa tentativa de sudo fica no log do sudo da máquina como qualquer outra, e um usuário fora do sudoers pode gerar o aviso do sudo ao administrador. O número de série só é coletado com `include_sensitive_identifiers` ativado no arquivo de configuração.

## Onde ficam os arquivos

| | Linux | Windows | macOS |
| --- | --- | --- | --- |
| Relatórios e planilha modelo | `~/Documentos/Invenux` (pasta Documentos do sistema) | `Documents\Invenux` | `~/Documents/Invenux` |
| Histórico (`snapshots.db`), chaves de host (`known_hosts`), logs | `~/.local/share/invenux` | `%LOCALAPPDATA%\Invenux` | `~/Library/Application Support/Invenux` |
| Configuração (`config.json`) | `~/.config/invenux` | `%APPDATA%\Invenux` | `~/Library/Application Support/Invenux` |

As pastas do nome antigo (`invent-ssh`) são copiadas na primeira execução.

## Segurança e privacidade

- A interface só escuta em `127.0.0.1`, com um token por execução e verificação do cabeçalho `Host` contra DNS rebinding.
- A senha SSH nunca é gravada em disco.
- As chaves de host usam confiança no primeiro acesso por padrão: chave nova é guardada, chave trocada é recusada. Desligue no painel SSH para aceitar só chaves já conhecidas.
- As exportações em planilha neutralizam valores que começam como fórmula; o relatório HTML escapa cada valor coletado.
- Sem telemetria. Além do SSH para as máquinas da sua lista, o único acesso é a leitura da última release na API do GitHub ao abrir (`api.github.com/repos/lucaswotta/invenux/releases/latest`); desligue em Sobre e ajustes. Atualizações são conferidas com o `SHA256SUMS` da release antes de abrir ou instalar.

Vulnerabilidades devem ser reportadas em privado, veja [SECURITY.md](SECURITY.md).

## Perguntas frequentes

**Ele altera alguma coisa nas máquinas?**
Não. O script só lê arquivos e executa comandos de leitura. Nada é gravado, nem em `/tmp`.

**Por que todas as minhas máquinas mostram um único pente de memória?**
Veja a linha **Slots** nos detalhes da máquina: ela mostra quantos slots estão ocupados do total da placa, com cada pente listado. Se aparecer indisponível, o usuário SSH não é root e não tem regra de sudo sem senha para o `dmidecode`, veja [O que é coletado](#o-que-é-coletado).

**Uma máquina aparece Offline, mas está ligada.**
A linha diz o motivo. "Não respondeu na rede" significa nenhuma resposta em cerca de 3 segundos (em geral desligada ou endereço errado); "Conexão recusada na porta N" significa que está ligada, mas o SSH está parado, bloqueado ou em outra porta (ajuste no painel SSH); "Sem resposta em N s" indica firewall ou rede lenta, então aumente o timeout no painel SSH.

**Tem instalador?**
Ainda não: o Windows recebe um `.exe`, o macOS um app e o Linux uma pasta com `install.sh`. Veja [Baixar](#baixar).

**Dá para inventariar máquinas Windows ou macOS?**
Não. Os alvos precisam ser Linux com SSH. O programa em si roda em Linux, Windows e macOS.

**Qual porta ele usa?**
A 22 por padrão. Troque no painel SSH ou com `--ssh-port` na linha de comando. Máquinas em outra porta ganham uma coluna `SSH_PORT` na planilha; células vazias usam a porta do painel.

**Dá para rodar sem a interface?**
Sim, veja a linha de comando acima. Ela exige chave privada.

## Limitações

- Os alvos precisam ser Linux com SSH.
- Os detalhes dos slots de memória exigem root ou sudo sem senha para o `dmidecode` no alvo.
- O tipo de armazenamento identifica discos virtuais pelo modelo/fabricante/nome ou por hipervisor detectado. A detecção de hipervisor também classifica discos repassados à VM como Virtual. Os demais discos usam nome/transporte NVMe e a flag de rotação do kernel; mídia não rotativa inclui flash USB.
- A linha de comando aceita só chave privada, não senha.

## Próximos passos

O trabalho planejado e os problemas conhecidos estão nas [issues](https://github.com/lucaswotta/invenux/issues): instaladores assinados, agente SSH e jump host, porta SSH por máquina, coletas agendadas com relatório de mudanças, comparação entre quaisquer dois snapshots e acessibilidade. Comentários e pull requests em qualquer uma delas são bem-vindos.

## Contribuir

Pull requests são bem-vindos. O [CONTRIBUTING.md](CONTRIBUTING.md) explica o ambiente, os testes, como adicionar um idioma e como os prints e GIFs deste README são gerados a partir de um parque fictício (`scripts/demo_server.py`, `scripts/capture_media.mjs`).

Se o Invenux te poupa uma volta por todas as máquinas, uma estrela no repositório ajuda outras pessoas a encontrá-lo.

## Licença

[MIT](LICENSE) © Lucas Motta
