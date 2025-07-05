# SmartFlow2.0 e Módulo de segurança para carrinhos de emergência 

Este repositório contém o projeto de controle de acesso desenvolvido para o carrinho de suprimentos "SmartFlow", uma iniciativa do grupo CodeNexus em parceria com o Hospital Infantil Sabará.

## Projeto

O projeto SmartFlow visa implementar um sistema de controle de acesso inteligente para carrinhos de emergência. O objetivo principal é aumentar a segurança e o rastreamento do uso desses carrinhos dentro do ambiente hospitalar para maior controle de acesso e estoque para a Farmácia Central e gestão de cada andar.

## Solução

A solução implementada utiliza um sistema de identificação por aproximação (RFID) para controlar o acesso ao carrinho. Apenas usuários com cartões autorizados podem destravar o carrinho de emergência. Cada tentativa de acesso (autorizada ou não) é registrada e enviada para uma plataforma de monitoramento remota, proporcionando visibilidade em tempo real para a **Farmácia Central** sobre quem acessou o carrinho e quando. Além disso, também é possivel visualizar um mapa de status de cada carrinho de maneira individual já que esse status sempre é enviado a cada novo acesso de abertura ou fechamento.

### Diagrama

![Diagrama](https://github.com/user-attachments/assets/8e21f055-2ecd-410a-8f9b-13293996e1e2)

O fluxo principal de dados ocorre quando um cartão RFID é lido pela antena. Essa informação é processada pelo ESP32 (Controle de Acesso) e enviada através do MQTT Broker para o IoT Agent MQTT. O IoT Agent converte esses dados para o formato NGSI V2 e os envia para o Orion Context Broker. O Orion então atualiza o contexto do carrinho e envia informações relevantes para o Dashboard e para o STH-Comet para armazenamento histórico no MongoDB Histórico. A Aplicação Web pode então acessar esses dados histórico

## Especificações

**Hardware:**
1. Microcontrolador: **ESP32**
2. Leitor de Cartão: **RFC522**
3. Feedback Visual: **LCD I2C 20x4 e 16x2** , LED Verde (Acesso Permitido), LED Vermelho (Acesso Negado)
4. Feedback Sonoro: Buzzer
5. Mecanismo de Travamento: **Servo motor** para acionamento das gavetas

**Máquina Virtual (VM):**
1. Provedor: **Microsoft Azure**
2. Sistema Operacional: **Linux (Ubuntu)**
3. Configuração: **Standard B1s (1 vCPU, 1 GiB de memória)**

**Software/Plataformas:**
1. **FIWARE** (Orion Context Broker, STH-Comet para gerenciamento e histórico de dados)
2. **Wokwi** (Plataforma de simulação para desenvolvimento)
3. **Arduino IDE** (Ambiente de desenvolvimento para o ESP32)
4. **Postman** (Ferramenta para testes de API e comunicação com a VM)

## Links Úteis

Link da Simulação no Wokwi: [Clique aqui](https://wokwi.com/projects/433399421274488833)

Link do Vídeo de Demonstração: [Clique aqui](https://youtu.be/HRn_Xj3Sltk)

## Integrantes da Equipe CodeNexus

- [Francisco Vargas](https://github.com/Franciscov25)
- [Kayque Carvalho](https://github.com/Kay-Carv)
- [Matheus Eiki](https://github.com/Matheus-Eiki)
- [Marcelo Affonso](https://github.com/tenebres-cpu)

**Contextualização:**

O grupo CodeNexus apresenta a atualização do sistema SmartFlow, uma solução de controle de acesso inteligente para o carrinho emergêcia médicos do **Hospital Infantil Sabará**. Nosso protótipo demonstra um sistema de controle de acesso em tempo real, visando maior visibilidade e controle sobre a utilização dos carrinhos, pavimentando o caminho para futuras implementações de controle de estoque e gestão de recursos.
