namespace DragoDeskHelp.API.DTOs
{
    public class TicketResponseDto
    {
        public string RoomNumber { get; set; } = string.Empty;

        public string AuthorName { get; set; } = string.Empty; 

        public string Description { get; set; } = string.Empty;

        public string Status { get; set; } = string.Empty;

        public string CreatedAt { get; set; } = string.Empty;
    }
}