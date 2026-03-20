using DragoDeskHelp.BLL.Services;
using DragoDeskHelp.Core.Interfaces;
using DragoDeskHelp.DAL;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("ApplicationDbContext")));

builder.Services.AddHttpClient<ITelegramBotService, TelegramBotService>(client => 
{
    client.BaseAddress = new Uri("http://bot:8000/"); 
});

builder.Services.AddScoped<ITicketService, TicketService>();

builder.Services.AddControllers();

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

var logger = app.Services.GetRequiredService<ILogger<Program>>();

// Database migrations setup
using (var scope = app.Services.CreateScope())
{
    try
    {
        var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();

        if (dbContext.Database.CanConnect())
        {
            logger.LogInformation("✅ PostgreSQL: connection successful.");
            dbContext.Database.Migrate();
        }
        else
            logger.LogError("❌ PostgreSQL: connection failed.");
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "❌ PostgreSQL connection error.");
    }
}


app.UseSwagger();
app.UseSwaggerUI();

app.UseHttpsRedirection();

app.UseCors("AllowAll");

app.MapControllers();

app.Run();