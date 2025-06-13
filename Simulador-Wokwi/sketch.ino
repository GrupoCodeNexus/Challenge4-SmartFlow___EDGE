#include <Arduino.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <SPI.h>
#include <MFRC522.h>

// --- Pinos RFID
#define SS_PIN 5
#define RST_PIN 4

// --- Pinos de controle
#define SERVO1_PIN 2
#define SERVO2_PIN 12
#define SERVO3_PIN 14
#define GREEN_LED 26
#define RED_LED 25
#define BUZZER_PIN 33
#define YELLOW_LED 27

// --- Objetos
Servo servo1, servo2, servo3;
LiquidCrystal_I2C lcd(0x27, 16, 2);
MFRC522 rfid(SS_PIN, RST_PIN);

// --- UIDs válidos
const String UID1_KEYS[] = { "D3 16 CF 9A", "4D 2E AB 10" };
const String UID2 = "BA AD DF 86";
const String UID3 = "46 A2 8A 3F";
const String MASTER_ID = "B3 9A 3A DA";
const String ID_LIBERACAO = "D2 DD 56 1B";

// --- Estado
bool portaAberta = false;
bool modoLiberado = false;
unsigned long tempoLiberacaoStart = 0;
const unsigned long TEMPO_LIMITE_LIBERACAO = 10000; // 10 segundos
String ultimoCartao = "";
String uidLiberado = "";

void setup() {
  Serial.begin(115200);
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
  fecharTodosServos();

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("   Code Nexus");
  delay(2000);
  mostrarTelaDeEspera();
}

void loop() {
  // --- Verifica se o tempo do modo liberado expirou
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

  // --- Fechamento com mesmo cartão
  if (portaAberta && uidStr == ultimoCartao) {
    fecharTodosServos();
    Serial.println("Fechando...");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Porta fechada");
    delay(2000);
    mostrarTelaDeEspera();
    portaAberta = false;
    ultimoCartao = "";
    uidLiberado = "";
    return;
  }

  // --- Master abre todos
  if (uidStr == MASTER_ID) {
    abrirTodosServos();
    portaAberta = true;
    ultimoCartao = uidStr;
    modoLiberado = false;
    digitalWrite(YELLOW_LED, LOW);
    return;
  }

  // --- Ativa modo liberado
  if (uidStr == ID_LIBERACAO) {
    modoLiberado = true;
    uidLiberado = "";
    tempoLiberacaoStart = millis();
    digitalWrite(YELLOW_LED, HIGH);
    Serial.println("Modo liberado ativado.");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Liberado acesso");
    lcd.setCursor(0, 1);
    lcd.print("Use seu cartao");
    delay(2000);
    mostrarTelaDeEspera();
    return;
  }

  // --- Durante modo liberado, permite abrir servo com cartão válido
  if (!portaAberta && modoLiberado) {
    if (isInArray(uidStr, UID1_KEYS, sizeof(UID1_KEYS) / sizeof(UID1_KEYS[0]))) {
      abrirPorta(servo1, uidStr);
    } else if (uidStr == UID2) {
      abrirPorta(servo2, uidStr);
    } else if (uidStr == UID3) {
      abrirPorta(servo3, uidStr);
    } else {
      negarAcesso("UID invalido");
      return;
    }

    uidLiberado = uidStr;
    portaAberta = true;
    ultimoCartao = uidStr;
    modoLiberado = false;
    digitalWrite(YELLOW_LED, LOW);
    return;
  }

  // --- Caso geral de negação
  negarAcesso("Acesso negado");
  digitalWrite(YELLOW_LED, LOW);
}

// --- Função auxiliar para verificar se valor está no array
bool isInArray(String val, const String arr[], size_t size) {
  for (size_t i = 0; i < size; i++) {
    if (val == arr[i]) return true;
  }
  return false;
}

void abrirPorta(Servo &servo, String input) {
  Serial.println("Acesso permitido: " + input);
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  digitalWrite(YELLOW_LED, LOW); // Apaga LED amarelo ao liberar

  servo.write(0);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Acesso permitido");
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
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  servo1.write(0);
  servo2.write(0);
  servo3.write(0);
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

void fecharTodosServos() {
  servo1.write(90);
  servo2.write(90);
  servo3.write(90);
}

void negarAcesso(String msg) {
  Serial.println(msg);
  digitalWrite(RED_LED, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Acesso negado");
  lcd.setCursor(0, 1);
  lcd.print(msg);
  delay(1000);
  digitalWrite(RED_LED, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(YELLOW_LED, LOW);
  mostrarTelaDeEspera();
}

void mostrarTelaDeEspera() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Passe o cartao");
  Serial.println("Aguardando cartao...");
  digitalWrite(YELLOW_LED, LOW);
}