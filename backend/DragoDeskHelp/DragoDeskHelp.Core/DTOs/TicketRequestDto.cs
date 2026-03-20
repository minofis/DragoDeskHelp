using System.ComponentModel.DataAnnotations;

namespace DragoDeskHelp.Core.DTOs
{
    public class TicketRequestDto
    {
        [Required]
        public string RoomNumber { get; set; } = string.Empty;

        [Required]
        public string AuthorName { get; set; } = string.Empty; 

        [Required]
        public string Description { get; set; } = string.Empty;
    }
}