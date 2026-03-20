using Microsoft.EntityFrameworkCore;
using DragoDeskHelp.DAL;
using DragoDeskHelp.Core.Enums;
using DragoDeskHelp.Core.Entities;
using DragoDeskHelp.Core.DTOs;
using DragoDeskHelp.Core.Interfaces;

namespace DragoDeskHelp.BLL.Services
{
    public class TicketService : ITicketService
    {
        private readonly AppDbContext _context;
        private readonly ITelegramBotService _telegramBotService;

        public TicketService(AppDbContext context, ITelegramBotService telegramBotService)
        {
            _context = context;
            _telegramBotService = telegramBotService;
        }

        public async Task<IEnumerable<TicketResponseDto>> GetTicketsAsync()
        {
            var rawTickets = await _context.Tickets
                .OrderByDescending(t => t.CreatedAt)
                .ToListAsync();

            var kyivTimeZone = TimeZoneInfo.FindSystemTimeZoneById("Europe/Kyiv");

            return rawTickets.Select(t => {
                var localTime = TimeZoneInfo.ConvertTimeFromUtc(t.CreatedAt, kyivTimeZone);

                return new TicketResponseDto
                {
                    Id = t.Id,
                    RoomNumber = t.RoomNumber,
                    AuthorName = t.AuthorName,
                    Description = t.Description,
                    StatusText = t.Status switch 
                    {
                        TicketStatus.New => "Нова",
                        TicketStatus.InProgress => "В роботі",
                        TicketStatus.Resolved => "Виконано",
                        TicketStatus.Closed => "Закрито",
                        _ => "Невідомо"
                    },
                    CreatedAt = localTime.ToString("dd.MM.yyyy HH:mm") 
                };
            });
        }

        public async Task<string> CreateTicketAsync(TicketRequestDto ticketDto)
        {
            var ticket = new Ticket
            {
                RoomNumber = ticketDto.RoomNumber,
                AuthorName = ticketDto.AuthorName,
                Description = ticketDto.Description,
                CreatedAt = DateTime.UtcNow,
                Status = TicketStatus.New
            };

            _context.Tickets.Add(ticket);
            await _context.SaveChangesAsync();

            string displayId = ticket.Id.ToString();

            await _telegramBotService.NotifyNewTicketAsync(
                displayId, 
                ticket.RoomNumber, 
                ticket.AuthorName, 
                ticket.Description);

            return displayId;
        }

        public async Task<bool> UpdateTicketStatusAsync(int id, TicketStatus newStatus)
        {
            var ticket = await _context.Tickets.FindAsync(id);
            
            if (ticket == null) 
                return false;

            ticket.Status = newStatus;
            await _context.SaveChangesAsync();

            return true;
        }
    }
}