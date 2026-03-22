using DragoDeskHelp.Core.DTOs;
using DragoDeskHelp.Core.Enums;

namespace DragoDeskHelp.Core.Interfaces
{
    public interface ITicketService
    {
        Task<IEnumerable<TicketResponseDto>> GetTicketsAsync(TicketStatus? status = null, string? assigneeId = null);

        Task<TicketResponseDto?> GetTicketByIdAsync(int id);

        Task<string> CreateTicketAsync(TicketRequestDto ticketDto);
        
        Task<bool> UpdateTicketStatusAsync(int id, TicketStatus newStatus, string? assigneeId = null);
    }
}