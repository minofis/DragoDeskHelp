using System.ComponentModel.DataAnnotations;
using DragoDeskHelp.Core.Enums;

namespace DragoDeskHelp.Core.Entities
{
    public class Ticket
    {
        public int Id { get; set; }

        [Required]
        public string RoomNumber { get; set; } = string.Empty;

        [Required]
        public string AuthorName { get; set; } = string.Empty; 

        [Required]
        public string Description { get; set; } = string.Empty;

        public TicketStatus Status { get; set; } = TicketStatus.New;

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    }
}