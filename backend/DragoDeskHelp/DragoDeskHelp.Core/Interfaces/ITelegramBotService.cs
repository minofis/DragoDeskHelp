namespace DragoDeskHelp.Core.Interfaces
{
    public interface ITelegramBotService
    {
        Task NotifyNewTicketAsync(string ticketId, string roomNumber, string authorName, string description);
    }
}