using Microsoft.AspNetCore.Mvc;
using DragoDeskHelp.Core.DTOs;
using DragoDeskHelp.Core.Interfaces;
using DragoDeskHelp.Core.Enums;

namespace DragoDeskHelp.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class TicketsController : ControllerBase
    {
        private readonly ITicketService _ticketService;

        public TicketsController(ITicketService ticketService)
        {
            _ticketService = ticketService;
        }

        [HttpGet]
        public async Task<ActionResult<IEnumerable<TicketResponseDto>>> GetTickets([FromQuery] TicketStatus? status)
        {
            var response = await _ticketService.GetTicketsAsync(status);
            return Ok(response);
        }

        [HttpPost]
        public async Task<ActionResult> CreateTicket(TicketRequestDto ticketDto)
        {
            var newTicketId = await _ticketService.CreateTicketAsync(ticketDto);
            
            return Ok(new { Message = "Заявка створена", Id = newTicketId });
        }

        [HttpPatch("{id}/status")]
        public async Task<IActionResult> UpdateTicketStatus(int id, 
            [FromBody] TicketStatusUpdateDto dto)
        {
            var isUpdated = await _ticketService.UpdateTicketStatusAsync(id, dto.Status);

            if (!isUpdated)
            {
                return NotFound(new { Message = $"Заявка з ID {id} не знайдена." });
            }

            return Ok(new { Message = "Статус успішно оновлено!" });
        }

        [HttpGet("{id}")]
        public async Task<ActionResult<TicketResponseDto>> GetTicket(int id)
        {
            var ticket = await _ticketService.GetTicketByIdAsync(id);
            
            if (ticket == null)
                return NotFound(new { Message = $"Заявка з ID {id} не знайдена." });

            return Ok(ticket);
        }
    }
}