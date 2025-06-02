import os
import re
import pandas as pd
from datetime import datetime
import shutil
import logging
import imaplib
import email
from email.header import decode_header
import tempfile
import chardet
import sys
import traceback

# Configurar encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class CVAutomationSystem:
    def __init__(self, base_folder="automacao_curriculos"):
        self.base_folder = base_folder
        self.cv_folder = os.path.join(base_folder, "curriculos")
        self.logs_folder = os.path.join(base_folder, "logs")
        self.planilha_path = os.path.join(base_folder, "candidatos.xlsx")
        
        self._setup_folders()
        self._setup_logging()
        self._setup_spreadsheet()
    
    def _setup_folders(self):
        folders = [self.base_folder, self.cv_folder, self.logs_folder]
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
    
    def _setup_logging(self):
        log_file = os.path.join(self.logs_folder, f"automacao_{datetime.now().strftime('%Y%m%d')}.log")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_spreadsheet(self):
        if os.path.exists(self.planilha_path):
            self.df_candidatos = pd.read_excel(self.planilha_path)
            self.logger.info("Planilha existente carregada")
        else:
            self.df_candidatos = pd.DataFrame(columns=[
                'Nome', 'Telefone', 'Vaga', 'Data_Candidatura', 
                'Arquivo_CV', 'Status', 'Observacoes'
            ])
            self.logger.info("Nova planilha criada")
    
    def extract_candidate_data(self, email_body):
        self.logger.debug(f"Extraindo dados do corpo:\n{email_body}")
        data = {'nome': None, 'telefone': None, 'vaga': None}
        
        # Tentar padrão específico (caso do Roberto)
        roberto_match = re.search(
            r'Nome completo:\s*([A-Za-zÀ-ÿ\s]+?)(?:\n|Vaga|\.)',
            email_body, 
            re.IGNORECASE
        )
        if roberto_match:
            data['nome'] = roberto_match.group(1).strip()
            self.logger.info("Dados extraídos usando padrão Roberto")
        
        # Padrões genéricos
        if not data['nome']:
            nome_match = re.search(
                r'(?:Nome|Nome completo)[:\s]*([A-Za-zÀ-ÿ\s]+?)(?:\n|Vaga|\.|$)',
                email_body, 
                re.IGNORECASE
            )
            if nome_match:
                data['nome'] = nome_match.group(1).strip()
        
        # Telefone
        telefone_match = re.search(
            r'(?:Telefone|Tel|Contato)[:\s]*([\d\s\(\)\-]+)',
            email_body, 
            re.IGNORECASE
        )
        if telefone_match:
            data['telefone'] = telefone_match.group(1).strip()
        
        # Vaga - removendo "de" no início da vaga.
        vaga_match = re.search(
            r'(?:Vaga|vaga de|para a vaga)[:\s]*(de\s)?([A-Za-zÀ-ÿ\s\-]+?)(?:\n|\.|$)',
            email_body, 
            re.IGNORECASE
        )
        if vaga_match:
            # Usar o grupo 2 para ignorar o "de" inicial
            data['vaga'] = vaga_match.group(2).strip()
        
        self.logger.info(f"Dados extraídos: {data}")
        return data
    
    def save_attachment(self, attachment_path, candidate_name):
        try:
            if not os.path.exists(attachment_path):
                self.logger.error(f"Anexo não encontrado: {attachment_path}")
                return None
            
            # Limpar nome do candidato para usar no nome do arquivo
            clean_name = re.sub(r'[^\w\s-]', '', candidate_name.strip())
            clean_name = re.sub(r'[-\s]+', '_', clean_name)
            
            # Manter a extensão original do arquivo
            file_ext = os.path.splitext(attachment_path)[1]
            new_filename = f"{clean_name}_CV{file_ext}"
            new_path = os.path.join(self.cv_folder, new_filename)
            
            shutil.copy2(attachment_path, new_path)
            self.logger.info(f"Anexo salvo: {new_path}")
            return new_filename
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar anexo: {str(e)}")
            return None
    
    def register_candidate(self, candidate_data, attachment_filename=None, status="Processado"):
        try:
            # Limpar nome do candidato antes de salvar
            clean_name = re.sub(r'[^\w\s-]', '', candidate_data.get('nome', 'N/A').strip())
            clean_name = re.sub(r'[-\s]+', ' ', clean_name)  # Manter espaços normais
            
            new_row = {
                'Nome': clean_name,
                'Telefone': candidate_data.get('telefone', 'N/A'),
                'Vaga': candidate_data.get('vaga', 'N/A'),
                'Data_Candidatura': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Arquivo_CV': attachment_filename or 'Sem anexo',
                'Status': status,
                'Observacoes': 'Erro: Anexo não encontrado' if attachment_filename is None else 'OK'
            }
            
            self.df_candidatos = pd.concat([self.df_candidatos, pd.DataFrame([new_row])], ignore_index=True)
            self.df_candidatos.to_excel(self.planilha_path, index=False)
            self.logger.info(f"Candidato registrado: {clean_name}")
            
        except Exception as e:
            self.logger.error(f"Erro ao registrar candidato: {str(e)}")
    
    def process_email(self, email_subject, email_body, attachment_path=None):
        self.logger.info(f"Processando email: {email_subject}")
        
        if not re.search(r'candidatura', email_subject, re.IGNORECASE):
            self.logger.warning("Email não é de candidatura, ignorando")
            return
        
        candidate_data = self.extract_candidate_data(email_body)
        
        if not candidate_data['nome']:
            self.logger.error("Nome do candidato não encontrado")
            self.register_candidate(candidate_data, status="Erro - Nome não encontrado")
            return
        
        attachment_filename = None
        if attachment_path:
            attachment_filename = self.save_attachment(attachment_path, candidate_data['nome'])
            if attachment_filename is None:
                self.register_candidate(candidate_data, status="Erro - Falha ao salvar anexo")
                return
        
        status = "Processado com sucesso" if attachment_filename else "Processado - Sem anexo"
        self.register_candidate(candidate_data, attachment_filename, status)
    
    def get_statistics(self):
        if len(self.df_candidatos) == 0:
            return "Nenhum candidato processado ainda"
        
        stats = {
            'Total de candidatos': len(self.df_candidatos),
            'Com currículo': len(self.df_candidatos[self.df_candidatos['Arquivo_CV'] != 'Sem anexo']),
            'Sem currículo': len(self.df_candidatos[self.df_candidatos['Arquivo_CV'] == 'Sem anexo']),
            'Processados com sucesso': len(self.df_candidatos[self.df_candidatos['Status'].str.contains('sucesso', na=False)]),
            'Com erros': len(self.df_candidatos[self.df_candidatos['Status'].str.contains('Erro', na=False)])
        }
        
        return stats

    def fetch_and_process_emails(self, imap_server, email_user, email_pass, folder="INBOX"):
        try:
            self.logger.info(f"Conectando ao servidor IMAP: {imap_server}")
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_user, email_pass)
            mail.select(folder)
            self.logger.info(f"Login bem-sucedido na conta: {email_user}")
            
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                self.logger.error("Falha ao buscar e-mails não lidos")
                return

            email_ids = messages[0].split()
            self.logger.info(f"E-mails não lidos encontrados: {len(email_ids)}")

            for eid in email_ids:
                attachment_path = None
                try:
                    eid_str = eid.decode('utf-8')
                    status, msg_data = mail.fetch(eid_str, '(RFC822)')
                    if status != 'OK' or not msg_data or not msg_data[0]:
                        continue
                    
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Decodificar assunto
                    subject = ""
                    for part, encoding in decode_header(msg["Subject"]):
                        if isinstance(part, bytes):
                            subject += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            subject += str(part)
                    
                    self.logger.info(f"Processando e-mail: {subject}")
                    
                    # Extrair corpo do e-mail
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    try:
                                        encoding = chardet.detect(payload)['encoding'] or 'utf-8'
                                        body += payload.decode(encoding, errors='replace')
                                    except:
                                        body += payload.decode('utf-8', errors='replace')
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            try:
                                encoding = chardet.detect(payload)['encoding'] or 'utf-8'
                                body = payload.decode(encoding, errors='replace')
                            except:
                                body = payload.decode('utf-8', errors='replace')
                    
                    # Processar anexos
                    for part in msg.walk():
                        if part.get_content_maintype() != 'multipart' and part.get_filename():
                            filename = part.get_filename()
                            
                            # Decodificar nome do arquivo
                            if isinstance(filename, bytes):
                                filename = filename.decode('utf-8', errors='ignore')
                            
                            # Salvar anexo temporariamente
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    temp_file.write(payload)
                                    attachment_path = temp_file.name
                                    self.logger.info(f"Anexo salvo temporariamente: {filename}")
                    
                    # Processar o e-mail
                    self.process_email(subject, body, attachment_path)
                    
                    # Marcar como lido
                    mail.store(eid_str, '+FLAGS', '\\Seen')
                    self.logger.info(f"E-mail marcado como lido: {subject}")
                    
                    # Limpar arquivo temporário
                    if attachment_path and os.path.exists(attachment_path):
                        try:
                            os.remove(attachment_path)
                        except Exception as e:
                            self.logger.error(f"Erro ao remover anexo temporário: {str(e)}")
                    
                except Exception as e:
                    self.logger.error(f"Erro ao processar e-mail ID {eid}: {str(e)}\n{traceback.format_exc()}")
            
            mail.close()
            mail.logout()
            self.logger.info("Conexão IMAP finalizada")
            
        except Exception as e:
            self.logger.error(f"Erro na conexão IMAP: {str(e)}\n{traceback.format_exc()}")


def main():
    sistema = CVAutomationSystem()
    
    # Configurações de e-mail
    IMAP_SERVER = "imap.gmail.com"  
    EMAIL_USER = "automacaoliber@gmail.com"
    EMAIL_PASS = "csxj oino alhq rmxu"  
    
    print("\n=== BUSCANDO E-MAIS REAIS ===")
    sistema.fetch_and_process_emails(IMAP_SERVER, EMAIL_USER, EMAIL_PASS)
    
    print("\n=== ESTATÍSTICAS FINAIS ===")
    stats = sistema.get_statistics()
    if isinstance(stats, dict):
        for key, value in stats.items():
            print(f"{key}: {value}")
    else:
        print(stats)
    
    print(f"\nArquivos gerados:")
    print(f"- Planilha: {sistema.planilha_path}")
    print(f"- Currículos: {sistema.cv_folder}")
    print(f"- Logs: {sistema.logs_folder}")

if __name__ == "__main__":
    main()
