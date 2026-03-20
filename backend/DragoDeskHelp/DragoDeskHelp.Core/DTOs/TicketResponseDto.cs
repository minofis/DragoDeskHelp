namespace DragoDeskHelp.Core.DTOs
{
    public class TicketResponseDto
    {
        public int Id { get; set; }
        public string RoomNumber { get; set; } = string.Empty;

        public string AuthorName { get; set; } = string.Empty; 

        public string Description { get; set; } = string.Empty;

        public string StatusText { get; set; } = string.Empty;

        public string CreatedAt { get; set; } = string.Empty;
    }
}