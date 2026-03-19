using DragoDeskHelp.Core.Entities;
using Microsoft.EntityFrameworkCore;

namespace DragoDeskHelp.DAL
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
        {
        }

        public DbSet<Ticket> Tickets { get; set; }
    }
}