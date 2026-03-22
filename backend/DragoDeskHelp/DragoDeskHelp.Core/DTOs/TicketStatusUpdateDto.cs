using System.ComponentModel.DataAnnotations;
using DragoDeskHelp.Core.Enums;

namespace DragoDeskHelp.Core.DTOs
{
    public class TicketStatusUpdateDto
    {
        [Required]
        public TicketStatus Status { get; set; }
        
        public string? AssigneeId { get; set; }
    }
}