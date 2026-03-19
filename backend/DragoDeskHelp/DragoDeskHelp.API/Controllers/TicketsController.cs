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
            var tickets = await _context.Tickets
                .Select(t => new TicketResponseDto
                {
                    RoomNumber = t.RoomNumber,
                    AuthorName = t.AuthorName,
                    Description = t.Description,
                    Status = t.Status.ToString(),
                    CreatedAt = t.CreatedAt.ToString()
                })
                .OrderByDescending(t => t.CreatedAt)
                .ToListAsync();

            return Ok(tickets);
        }

        [HttpPost]
        public async Task<ActionResult<Ticket>> CreateTicket(TicketRequestDto ticketDto)
        {
            var ticket = new Ticket
            {
                Id = Guid.NewGuid(),
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