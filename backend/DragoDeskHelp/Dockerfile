# Stage 1: Build
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build

WORKDIR /src

# copy csproj files
COPY DragoDeskHelp.API/DragoDeskHelp.API.csproj DragoDeskHelp.API/
COPY DragoDeskHelp.BLL/DragoDeskHelp.BLL.csproj DragoDeskHelp.BLL/
COPY DragoDeskHelp.DAL/DragoDeskHelp.DAL.csproj DragoDeskHelp.DAL/
COPY DragoDeskHelp.Core/DragoDeskHelp.Core.csproj DragoDeskHelp.Core/

# restore
RUN dotnet restore DragoDeskHelp.API/DragoDeskHelp.API.csproj

# copy source code
COPY DragoDeskHelp.API/ DragoDeskHelp.API/
COPY DragoDeskHelp.BLL/ DragoDeskHelp.BLL/
COPY DragoDeskHelp.DAL/ DragoDeskHelp.DAL/
COPY DragoDeskHelp.Core/ DragoDeskHelp.Core/

# build
WORKDIR /src/DragoDeskHelp.API
RUN dotnet build -c Release -o /app/build

# Stage 2: Publish
FROM build AS publish
RUN dotnet publish -c Release -o /app/publish

# Stage 3: Runtime
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final

ENV ASPNETCORE_URLS=http://+:5001
WORKDIR /app
COPY --from=publish /app/publish .

EXPOSE 5001

ENTRYPOINT ["dotnet", "DragoDeskHelp.API.dll"]