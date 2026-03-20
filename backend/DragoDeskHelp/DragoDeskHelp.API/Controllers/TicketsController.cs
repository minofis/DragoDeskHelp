using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using DragoDeskHelp.DAL;
using DragoDeskHelp.Core.Enums;
using DragoDeskHelp.Core.Entities;
using DragoDeskHelp.API.DTOs;

namespace DragoDeskHelp.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class TicketsController : ControllerBase
    {
        private readonly AppDbContext _context;

        public TicketsController(AppDbContext context)
        {
            _context = context;
        }

        [HttpGet]
        public async Task<ActionResult<IEnumerable<TicketResponseDto>>> GetTickets()
        {
            var rawTickets = await _context.Tickets
                .OrderByDescending(t => t.CreatedAt)
                .ToListAsync();

            var kyivTimeZone = TimeZoneInfo.FindSystemTimeZoneById("Europe/Kyiv");

            var response = rawTickets.Select(t => {
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

            return Ok(response);
        }

        [HttpPost]
        public async Task<ActionResult<Ticket>> CreateTicket(TicketRequestDto ticketDto)
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

            return CreatedAtAction(nameof(GetTickets), new { id = ticket.Id }, ticket);
        }
    }
}