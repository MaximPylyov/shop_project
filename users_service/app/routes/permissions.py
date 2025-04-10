import bcrypt
import uuid
from typing import List, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth_services import get_current_roles
from database import get_session
import models
import schemas

router = APIRouter(prefix="/permissions", tags=["Permission"])

@router.get("/", response_model=List[schemas.Permission])
async def get_permissions(roles: set = Depends(get_current_roles), db: AsyncSession = Depends(get_session)):
    if 'Admin' not in roles:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(
            select(models.Permission).options(selectinload(models.Permission.roles))
        )
        permissions = result.scalars().all()
        return permissions
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Ошибка при отборе списка доступов")


@router.post("/", response_model=schemas.Permission)
async def create_permission(permission: schemas.PermissionCreate, roles: set = Depends(get_current_roles), db: AsyncSession = Depends(get_session)):
    if 'Admin' not in roles:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(
            select(models.Permission).filter(models.Permission.name == permission.name)
        )
        db_permission = result.scalar_one_or_none()
        if db_permission:
            raise HTTPException(status_code=400, detail="Доступ с таким названием уже есть")
        
        permission_data = permission.model_dump()
        permission_data["id"] = uuid.uuid4()
        db_permission = models.Permission(**permission_data)
        
        db.add(db_permission)
        await db.commit()
        await db.refresh(db_permission)
        return db_permission
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании доступа {e}")
    

@router.put("/{permission_id}", response_model=schemas.Permission)
async def edit_permission(permission_id: UUID, permission: schemas.PermissionUpdate, roles: set = Depends(get_current_roles), db: AsyncSession = Depends(get_session)):
    if 'Admin' not in roles:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        if permission.name:
            existing_permission = await db.execute(
                select(models.Permission).filter(
                    models.Permission.name == permission.name,
                    models.Permission.id != permission_id
                )
            )
            if existing_permission.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Доступ с таким названием уже существует")
        
        result = await db.execute(
            select(models.Permission)
            .options(selectinload(models.Permission.roles))
            .filter(models.Permission.id == permission_id)
        )
        db_permission = result.scalar_one_or_none()
        
        if not db_permission:
            raise HTTPException(status_code=404, detail="Указанный доступ не найден")
        
        permission_data = permission.model_dump(exclude_unset=True)
        for field, value in permission_data.items():
            setattr(db_permission, field, value)
        
        await db.commit()
        await db.refresh(db_permission)
        return db_permission
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении доступа {e}")
    


@router.delete("/{permission_id}")
async def delete_permission(permission_id: UUID, roles: set = Depends(get_current_roles), db: AsyncSession = Depends(get_session)):
    if 'Admin' not in roles:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(
            select(models.Permission)
            .options(selectinload(models.Permission.roles))
            .filter(models.Permission.id == permission_id)
        )
        db_permission = result.scalar_one_or_none()
        
        if not db_permission:
            raise HTTPException(status_code=404, detail="Указанный доступ не найден")
            
        if db_permission.roles:
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить доступ, так как есть связанные роли"
            )
        
        await db.delete(db_permission)
        await db.commit()
        return {"message": "Доступ удален"} 

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных при удалении доступа {e}")
    

@router.post("/{permission_id}/roles/{role_id}")
async def assign_permission_to_role(
    permission_id: UUID,
    role_id: UUID,
    roles: set = Depends(get_current_roles),
    db: AsyncSession = Depends(get_session)
):
    if 'Admin' not in roles:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        permission_result = await db.execute(
            select(models.Permission).filter(models.Permission.id == permission_id)
        )
        permission = permission_result.scalar_one_or_none()
        if not permission:
            raise HTTPException(status_code=404, detail="Указанный доступ не найден")

        role_result = await db.execute(
            select(models.Role).filter(models.Role.id == role_id)
        )
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Указанная роль не найдена")


        existing_assignment = await db.execute(
            select(models.RolePermission).filter(
                and_(
                    models.RolePermission.permission_id == permission_id,
                    models.RolePermission.role_id == role_id
                )
            )
        )
        if existing_assignment.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Этот доступ уже назначен данной роли")

        new_assignment = models.RolePermission(
            id=uuid.uuid4(),
            permission_id=permission_id,
            role_id=role_id
        )
        db.add(new_assignment)
        await db.commit()

        return {"message": "Доступ успешно назначен роли"}

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при назначении доступа роли: {e}")

@router.delete("/{permission_id}/roles/{role_id}")
async def remove_permission_from_role(
    permission_id: UUID,
    role_id: UUID,
    roles: set = Depends(get_current_roles),
    db: AsyncSession = Depends(get_session)
):
    if 'Admin' not in roles:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(
            select(models.RolePermission).filter(
                and_(
                    models.RolePermission.permission_id == permission_id,
                    models.RolePermission.role_id == role_id
                )
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Указанный доступ не назначен данной роли")

        await db.delete(assignment)
        await db.commit()

        return {"message": "Доступ успешно удален у роли"}

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении доступа у роли: {e}")
    
