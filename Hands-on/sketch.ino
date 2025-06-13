#include <Arduino.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>          // <-- MUDANÇA: Adicionado
#include <PubSubClient.h>  // <-- MUDANÇA: Adicionado

// --- Configurações de Rede e MQTT ---
const char* SSID = "Wokwi-GUEST"; 
const char* PASSWORD = "";        
const char* BROKER_MQTT = "130.131.16.56"; 
const int BROKER_PORT = 1883;
const char* ID_MQTT = "fiware_nexus_003"; // <-- MUDANÇA: ID MQTT único

// --- Tópicos MQTT (baseado nos novos atributos) ---
const char* TOPICO_CMD = "/TEF/NEXUScode2/cmd";
const char* TOPICO_ESTADO = "/TEF/NEXUScode2/attrs/s";
const char* TOPICO_PERMITIDO = "/TEF/NEXUScode2/attrs/a";
const char* TOPICO_NEGADO = "/TEF/NEXUScode2/attrs/n";
const char* TOPICO_ABERTO = "/TEF/NEXUScode2/attrs/o";
const char* TOPICO_FECHADO = "/TEF/NEXUScode2/attrs/c";

// --- Pinos RFID ---
#define SS_PIN 5
#define RST_PIN 4

// --- Pinos de controle ---
#define SERVO1_PIN 13
#define SERVO2_PIN 12
#define SERVO3_PIN 14
#define GREEN_LED 26
#define RED_LED 25
#define BUZZER_PIN 33
#define YELLOW_LED 27

// --- Objetos ---
WiFiClient espClient;         // <-- MUDANÇA: Adicionado
PubSubClient MQTT(espClient); // <-- MUDANÇA: Adicionado
Servo servo1, servo2, servo3;
LiquidCrystal_I2C lcd(0x27, 16, 2);
MFRC522 rfid(SS_PIN, RST_PIN);

// --- UIDs válidos ---
const String UID1_KEYS[] = { "D3 16 CF 9A", "4D 2E AB 10" };
const String UID2 = "BA AD DF 86";
const String UID3 = "46 A2 8A 3F";
const String MASTER_ID = "B3 9A 3A DA";
const String ID_LIBERACAO = "D2 DD 56 1B";

// --- Variáveis de Estado ---
bool portaAberta = false;
bool modoLiberado = false;
unsigned long tempoLiberacaoStart = 0;
const unsigned long TEMPO_LIMITE_LIBERACAO = 10000; // 10 segundos
String ultimoCartao = "";
String uidLiberado = "";

// --- Protótipos de Funções ---
void negarAcesso(String msg, String uid); // <-- MUDANÇA: Assinatura alterada
void mostrarTelaDeEspera();
void fecharTodosServos(String uid); // <-- MUDANÇA: Assinatura alterada

// --- Funções de Conexão (do código antigo) ---
void initWiFi() {
  delay(10);
  Serial.println("Conectando-se ao Wi-Fi...");
  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi conectado. IP: ");
  Serial.println(WiFi.localIP());
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  // Por enquanto não faremos nada com comandos recebidos
  Serial.print("Mensagem recebida no tópico: ");
  Serial.println(topic);
}

void reconnectMQTT() {
  while (!MQTT.connected()) {
    Serial.print("Conectando ao MQTT...");
    if (MQTT.connect(ID_MQTT)) {
      Serial.println("Conectado.");
      MQTT.subscribe(TOPICO_CMD);
    } else {
      Serial.print("Erro: ");
      Serial.print(MQTT.state());
      Serial.println(" tentando novamente em 2 segundos...");
      delay(2000);
    }
  }
}


void setup() {
  Serial.begin(115200);
  
  // --- Inicialização da Rede ---
  initWiFi(); // <-- MUDANÇA: Adicionado
  MQTT.setServer(BROKER_MQTT, BROKER_PORT); // <-- MUDANÇA: Adicionado
  MQTT.setCallback(mqtt_callback);          // <-- MUDANÇA: Adicionado

  // --- Inicialização do Hardware ---
  SPI.begin();
  rfid.PCD_Init();

  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);

  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  servo3.setPeriodHertz(50);
  servo1.attach(SERVO1_PIN, 500, 2400);
  servo2.attach(SERVO2_PIN, 500, 2400);
  servo3.attach(SERVO3_PIN, 500, 2400);
  
  // Ação de fechar sem UID no início
  servo1.write(90); 
  servo2.write(90);
  servo3.write(90);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("   Code Nexus");
  delay(2000);
  mostrarTelaDeEspera();
}

void loop() {
  // --- Manutenção da Conexão MQTT ---
  if (!MQTT.connected()) reconnectMQTT(); // <-- MUDANÇA: Adicionado
  MQTT.loop();                             // <-- MUDANÇA: Adicionado

  // --- Lógica de Liberação por Tempo ---
  if (modoLiberado && millis() - tempoLiberacaoStart > TEMPO_LIMITE_LIBERACAO) {
    modoLiberado = false;
    digitalWrite(YELLOW_LED, LOW);
    Serial.println("Tempo de liberacao expirou.");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Tempo expirado");
    delay(2000);
    mostrarTelaDeEspera();
  }

  // --- Lógica de Leitura RFID ---
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;

  String uidStr = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uidStr += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uidStr += String(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) uidStr += " ";
  }
  uidStr.toUpperCase();
  Serial.println("Lido: " + uidStr);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Verificando...");
  delay(1000);

  // --- Lógica de Fechamento com o mesmo cartão ---
  if (portaAberta && uidStr == ultimoCartao) {
    fecharTodosServos(uidStr); // Passa o UID que fechou
    portaAberta = false;
    ultimoCartao = "";
    uidLiberado = "";
    return;
  }

  // --- Lógica de Abertura (Master, Liberado, etc.) ---
  if (uidStr == MASTER_ID) {
    abrirTodosServos();
    portaAberta = true;
    ultimoCartao = uidStr;
    modoLiberado = false;
    digitalWrite(YELLOW_LED, LOW);
    return;
  }
  
  if (uidStr == ID_LIBERACAO) {
    modoLiberado = true;
    tempoLiberacaoStart = millis();
    digitalWrite(YELLOW_LED, HIGH);
    Serial.println("Modo liberado ativado.");
    // ... (restante da lógica do LCD) ...
    return;
  }

  if (!portaAberta && modoLiberado) {
    bool acessoConcedido = false;
    if (isInArray(uidStr, UID1_KEYS, sizeof(UID1_KEYS) / sizeof(UID1_KEYS[0]))) {
      abrirPorta(servo1, uidStr);
      acessoConcedido = true;
    } else if (uidStr == UID2) {
      abrirPorta(servo2, uidStr);
      acessoConcedido = true;
    } else if (uidStr == UID3) {
      abrirPorta(servo3, uidStr);
      acessoConcedido = true;
    }

    if(acessoConcedido) {
      portaAberta = true;
      ultimoCartao = uidStr;
      modoLiberado = false;
      digitalWrite(YELLOW_LED, LOW);
    } else {
      negarAcesso("UID invalido", uidStr);
    }
    return;
  }

  // --- Negação Padrão ---
  negarAcesso("Acesso negado", uidStr);
  digitalWrite(YELLOW_LED, LOW);
}

// --- Funções Auxiliares e de Ação ---

bool isInArray(String val, const String arr[], size_t size) {
  for (size_t i = 0; i < size; i++) {
    if (val == arr[i]) return true;
  }
  return false;
}

void abrirPorta(Servo &servo, String uid) {
  Serial.println("Acesso permitido: " + uid);
  
  // <-- MUDANÇA: Publica no MQTT ---
  MQTT.publish(TOPICO_PERMITIDO, uid.c_str());
  MQTT.publish(TOPICO_ABERTO, uid.c_str());
  MQTT.publish(TOPICO_ESTADO, "aberto");

  // --- Lógica de Hardware ---
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  servo.write(0); // Abre o servo específico
  
  // --- Feedback Visual ---
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Acesso Permitido");
  delay(1000);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Passe o mesmo");
  lcd.setCursor(0, 1);
  lcd.print("cartao para fechar");
}

void abrirTodosServos() {
  Serial.println("MASTER: Abrindo todos os servos...");

  // <-- MUDANÇA: Publica no MQTT ---
  MQTT.publish(TOPICO_PERMITIDO, MASTER_ID.c_str());
  MQTT.publish(TOPICO_ABERTO, MASTER_ID.c_str());
  MQTT.publish(TOPICO_ESTADO, "aberto");

  // --- Lógica de Hardware e Feedback ---
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  servo1.write(180);
  servo2.write(180);
  servo3.write(180);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("MASTER liberado!");
  delay(1000);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Passe o mesmo");
  lcd.setCursor(0, 1);
  lcd.print("ID p/ fechar");
}

void fecharTodosServos(String uid) { // <-- MUDANÇA: Recebe o UID
  Serial.println("Fechando com o UID: " + uid);
  
  // <-- MUDANÇA: Publica no MQTT ---
  MQTT.publish(TOPICO_FECHADO, uid.c_str());
  MQTT.publish(TOPICO_ESTADO, "fechado");

  // --- Lógica de Hardware e Feedback ---
  servo1.write(90);
  servo2.write(90);
  servo3.write(90);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Porta fechada");
  delay(2000);
  mostrarTelaDeEspera();
}

void negarAcesso(String msg, String uid) { // <-- MUDANÇA: Recebe o UID
  Serial.println(msg + " UID: " + uid);

  // <-- MUDANÇA: Publica no MQTT ---
  MQTT.publish(TOPICO_NEGADO, uid.c_str());

  // --- Lógica de Hardware e Feedback ---
  digitalWrite(RED_LED, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Acesso negado");
  delay(1000);
  digitalWrite(RED_LED, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  mostrarTelaDeEspera();
}

void mostrarTelaDeEspera() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Passe o cartao");
  Serial.println("\nAguardando cartao...");
  digitalWrite(YELLOW_LED, LOW);
}
esse código serve para a vida real eu quero que ele seja usado dentro de um simulador mas não tire nenhuma função do servo ou led