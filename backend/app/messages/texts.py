"""Todos os textos do bot ficam aqui, fora da lógica de fluxo."""

def greet_new(oficina: str) -> str:
    return f"Olá! 👋 Seja bem-vindo à {oficina}! Como podemos ajudar?"


def greet_known(nome: str, oficina: str) -> str:
    return f"Olá, {nome}! 👋 Que bom falar com você de novo. Como podemos ajudar?"


def site_greeting(servico: str) -> str:
    return (f"Olá! 👋 Vi que você veio pelo site e quer agendar uma avaliação para o serviço de *{servico}*. "
            "Vamos organizar isso rapidinho.")


def site_greeting_known(nome: str, servico: str) -> str:
    return (f"Olá, {nome}! 👋 Vi que você veio pelo site e quer agendar uma avaliação para o serviço de "
            f"*{servico}*. Vamos continuar?")


INVALID = "Hmm, não consegui identificar essa opção. 😅 Pode escolher uma das opções abaixo?"
INVALID_HINT = "\n\nSe preferir, digite *atendente* para falar com nossa equipe ou *menu* para voltar ao início."
INVALID_TEXT = "Desculpe, não entendi essa informação. 😅 Pode tentar novamente?"

ASK_NAME = "Para começarmos, qual é o seu nome?"
NAME_OK = "Prazer, {nome}! 😊"
ASK_SERVICE = "Qual serviço você tem interesse em avaliar?"
SERVICES_TITLE = "Estes são os serviços da {oficina}. Qual deles você quer conhecer?"
SERVICE_DETAIL_ASK = "Deseja agendar uma avaliação presencial para este serviço?"

TRIAGE_ASK = "O que aconteceu com o veículo?"
TRIAGE_SUGGEST = "Pelo que você descreveu, o serviço *pode* ser {servico}. A confirmação é feita na avaliação presencial."
PHOTOS_OFFER = (
    "Sem problema! Você pode enviar algumas fotos da área que precisa de atendimento. 📸 "
    "Elas serão utilizadas apenas para ajudar nossa equipe a entender o problema e deixar seu atendimento "
    "mais preparado. A avaliação do veículo e qualquer orçamento são realizados presencialmente na oficina."
)
PHOTOS_WAIT = "Pode enviar as fotos por aqui. Quando terminar, toque em *Continuar*."
PHOTO_OK = "Recebi a foto! ✅ Pode enviar mais ou tocar em *Continuar*."
PHOTO_FAIL = "Não consegui receber essa imagem. Pode tentar de novo? (formatos aceitos: JPG, PNG ou WebP)"

ASK_VEHICLE_CHOOSE = "Para qual veículo será a avaliação?"
ASK_MAKE_MODEL = "Qual é a marca e o modelo do veículo? (por exemplo: Honda Civic)"
ASK_YEAR = "Qual é o ano do veículo?"
ASK_PLATE = "E qual é a placa? Se preferir, pode pular."
ASK_DESCRIPTION = ("Quer contar em poucas palavras o que aconteceu com o veículo? "
                   "Isso ajuda nossa equipe a se preparar. Se preferir, é só pular.")
ASK_DATE = "Perfeito! Em qual dia você prefere levar o veículo para a avaliação?"
ASK_TIME = "Certo! Estes são os horários disponíveis para {data}:"
NO_DAYS = ("No momento não encontrei horários disponíveis. Vou encaminhar seu atendimento para nossa equipe "
           "encontrar a melhor opção. 👨‍🔧")
SLOT_TAKEN = "Esse horário acabou de ser ocupado. 😕 Vou mostrar os horários que ainda estão livres."

HANDOFF = "Claro! Vou encaminhar seu atendimento para nossa equipe. 👨‍🔧 Em breve alguém vai falar com você por aqui."


def confirm_summary(nome: str, servico: str, veiculo: str, data: str, hora: str) -> str:
    return (f"Confira os dados da sua avaliação, {nome}:\n\n"
            f"• Serviço de interesse: {servico}\n• Veículo: {veiculo}\n• Data: {data}\n• Horário: {hora}\n\n"
            "Lembrando que é uma *avaliação presencial*: o orçamento é feito pela nossa equipe na oficina. Posso confirmar?")


def scheduled(nome: str, data: str, hora: str, endereco: str) -> str:
    txt = (f"Perfeito, {nome}! Sua avaliação ficou agendada para {data}, às {hora}. 🚗\n\n"
           "Pedimos que compareça à Oficina Castillo com o veículo nesse horário.\n\n"
           "A avaliação e o orçamento serão realizados presencialmente pela nossa equipe.")
    if endereco:
        txt += f"\n\n📍 {endereco}"
    return txt


def rescheduled(nome: str, data: str, hora: str) -> str:
    return (f"Pronto, {nome}! Sua avaliação foi reagendada para {data}, às {hora}. 🚗\n\n"
            "Continuamos te esperando na oficina com o veículo.")


NO_APPOINTMENTS = "Você não tem avaliações futuras agendadas. Quer agendar uma?"
LIST_APPOINTMENTS = "Estas são as suas avaliações agendadas. Qual delas você quer ver?"


def appointment_detail(data: str, hora: str, servico: str, veiculo: str, status: str) -> str:
    return (f"Sua avaliação:\n\n• Data: {data}\n• Horário: {hora}\n• Serviço de interesse: {servico}\n"
            f"• Veículo: {veiculo}\n• Situação: {status}\n\nO que você deseja fazer?")


TOO_LATE = ("Como a avaliação está muito próxima, não consigo alterá-la por aqui. "
            "Vou chamar nossa equipe para te ajudar. 👨‍🔧")
CANCEL_ASK = "Tem certeza que deseja cancelar esta avaliação?"
CANCELED = "Tudo certo, sua avaliação foi cancelada. Se precisar, é só chamar para agendar outra. 🙂"
KEPT = "Combinado, mantive sua avaliação como está."
FLOW_CANCELED = "Sem problemas, não agendei nada. Se precisar, é só chamar."
