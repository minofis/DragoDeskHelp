using System.Net.Http.Json;
using DragoDeskHelp.Core.Interfaces;

namespace DragoDeskHelp.BLL.Services
{
    public class TelegramBotService : ITelegramBotService
    {
        private readonly HttpClient _httpClient;

        public TelegramBotService(HttpClient httpClient)
        {
            _httpClient = httpClient;
        }

        public async Task NotifyNewTicketAsync(string ticketId, string roomNumber, string authorName, string description)
        {
            try
            {
                var payload = new 
                { 
                    id = ticketId, 
                    room = roomNumber,
                    author = authorName,
                    description = description
                };

                await _httpClient.PostAsJsonAsync("notify", payload);
                
                Console.WriteLine($"[TelegramBotService] Успешно отправлено уведомление для заявки {ticketId}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[TelegramBotService] ВНИМАНИЕ: Ошибка при отправке в Телеграм: {ex.Message}");
            }
        }
    }
}